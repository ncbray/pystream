import collections
import itertools
import util

import base

from . import canonicalobjects
from . import extendedtypes
from . import setmanager

from constraintextractor import ExtractDataflow

from constraints import AssignmentConstraint, DirectCallConstraint

# Only used for creating return variables
from language.python import ast
from language.python import program
from language.python import annotations

from optimization.callconverter import callConverter

from util.fold import foldFunction

from analysis.astcollector import getOps

from . cpadatabase import CPADatabase

# For keeping track of how much time we spend decompiling.
import time

import util.canonical

# For allocation
import types

#########################
### Utility functions ###
#########################

def foldFunctionIR(extractor, func, vargs=(), kargs={}):
	newvargs = [arg.pyobj for arg in vargs]

	assert not kargs, kargs
	newkargs = {}

	result = foldFunction(func, newvargs, newkargs)
	return extractor.getObject(result)


###############################
### Main class for analysis ###
###############################

externalOp  = util.canonical.Sentinel('<externalOp>')




class InterproceduralDataflow(object):
	def __init__(self, console, extractor, opPathLength=0):
		self.decompileTime = 0
		self.console   = console
		self.extractor = extractor

		# Has the context been constructed?
		self.liveContexts = set()

		self.liveCode = set()

		# The value of every slot
		self.setManager = setmanager.CachedSetManager()

		# Constraint information
		self.constraintReads   = collections.defaultdict(set)
		self.constraintWrites  = collections.defaultdict(set)
		self.constraints = set()

		# The worklist
		self.dirty = collections.deque()

		self.canonical = canonicalobjects.CanonicalObjects()

		# Information for contextual operations.
		self.opAllocates      = collections.defaultdict(set)
		self.opReads          = collections.defaultdict(set)
		self.opModifies       = collections.defaultdict(set)
		self.opInvokes        = collections.defaultdict(set)

		self.codeContexts     = collections.defaultdict(set)

		# HACK?
		self.codeContexts[base.externalFunction].add(base.externalFunctionContext)


		self.entryPointDescs = []

		self.db = CPADatabase()
		self.db.canonical = self.canonical # HACK so the canonical objects are accessable.
		self.db.system = self # HACK even bigger hack...

		# For vargs
		self.tupleClass = self.extractor.getObject(tuple)
		self.ensureLoaded(self.tupleClass)

		# For kargs
		self.dictionaryClass = self.extractor.getObject(dict)
		self.ensureLoaded(self.dictionaryClass)

		# Cache common slot names
		self.typeSlotName     = self.canonical.fieldName('LowLevel', self.extractor.getObject('type'))
		self.lengthSlotName   = self.canonical.fieldName('LowLevel', self.extractor.getObject('length'))

		# Controls how many previous ops are remembered by a context.
		# TODO remember prior CPA signatures?
		self.opPathLength = opPathLength
		self.cache = {}

		# The storage graph
		self.roots  = storegraph.RegionGroup()

		self.entryPointOp = {}
		self.entryPointReturn = {}

	def initalOpPath(self):
		if self.opPathLength == 0:
			path = None
		elif self.opPathLength == 1:
			path = externalOp
		else:
			path = (externalOp,)*self.opPathLength

		return self.cache.setdefault(path, path)

	def advanceOpPath(self, original, op):
		assert not isinstance(op, base.OpContext)

		if self.opPathLength == 0:
			path = None
		elif self.opPathLength == 1:
			path = op
		else:
			path = original[1:]+(op,)

		return self.cache.setdefault(path, path)
	def ensureLoaded(self, obj):
		start = time.clock()
		self.extractor.ensureLoaded(obj)
		self.decompileTime += time.clock()-start

	def getCall(self, obj):
		start = time.clock()
		result = self.extractor.getCall(obj)
		self.decompileTime += time.clock()-start
		return result

	def logAllocation(self, cop, cobj):
		assert isinstance(cobj, storegraph.ObjectNode), type(cobj)
		self.opAllocates[(cop.code, cop.op, cop.context)].add(cobj)


	def logRead(self, cop, slot):
		assert isinstance(slot, storegraph.SlotNode), type(slot)
		self.opReads[(cop.code, cop.op, cop.context)].add(slot)


	def logModify(self, cop, slot):
		assert isinstance(slot, storegraph.SlotNode), type(slot)
		self.opModifies[(cop.code, cop.op, cop.context)].add(slot)


	def constraint(self, constraint):
		self.constraints.add(constraint)

	def _signature(self, code, selfparam, params):
		assert code.isAbstractCode(), type(code)
		assert selfparam is None or selfparam is util.cpa.Any or isinstance(selfparam,  extendedtypes.ExtendedType), selfparam
		for param in params:
			assert param is util.cpa.Any or isinstance(param, extendedtypes.ExtendedType), param

		return util.cpa.CPASignature(code, selfparam, params)

	def canonicalContext(self, srcOp, code, selfparam, params):
		assert isinstance(srcOp, base.OpContext), type(srcOp)
		assert code.isAbstractCode(), type(code)

		sig     = self._signature(code, selfparam, params)
		opPath  = self.advanceOpPath(srcOp.context.opPath, srcOp.op)
		context = self.canonical._canonicalContext(sig, opPath, self.roots)

		# Mark that we created the context.
		self.codeContexts[code].add(context)

		return context

	def setTypePointer(self, obj):
		assert isinstance(obj, storegraph.ObjectNode), type(obj)
		xtype = obj.xtype

		if not xtype.isExisting():
			# Makes sure the type pointer is valid.
			self.ensureLoaded(xtype.obj)

			# Get the type object
			typextype = self.canonical.existingType(xtype.obj.type)

			field = obj.field(self, self.typeSlotName, obj.region.group.regionHint)
			field.initializeType(self, typextype)

	def existingSlotRef(self, xtype, slotName):
		assert xtype.isExisting()
		assert not slotName.isRoot()

		obj = xtype.obj
		assert isinstance(obj, program.AbstractObject), obj
		self.ensureLoaded(obj)

		slottype, key = slotName.type, slotName.name

		assert isinstance(key, program.AbstractObject), key

		if isinstance(obj, program.Object):
			if slottype == 'LowLevel':
				subdict = obj.lowlevel
			elif slottype == 'Attribute':
				subdict = obj.slot
			elif slottype == 'Array':
				# HACK
				if isinstance(obj.pyobj, list):
					return set([self.canonical.existingType(t) for t in obj.array.itervalues()])

				subdict = obj.array
			elif slottype == 'Dictionary':
				subdict = obj.dictionary
			else:
				assert False, slottype

			if key in subdict:
				return (self.canonical.existingType(subdict[key]),)

		# Not found
		return None

	def extendedInstanceType(self, context, xtype, op):
		self.ensureLoaded(xtype.obj)
		instObj = xtype.obj.abstractInstance()

		pyobj = xtype.obj.pyobj
		if pyobj is types.MethodType:
			# Method types are named by their function and instance
			sig = context.signature
			# TODO check that this is "new"?
			if len(sig.params) == 4:
				# sig.params[0] is the type object for __new__
				func = sig.params[1]
				inst = sig.params[2]
				return self.canonical.methodType(func, inst, instObj, op)
		elif pyobj is types.TupleType or pyobj is types.ListType or pyobj is types.DictionaryType:
			# Containers are named by the signature of the context they're allocated in.
			return self.canonical.contextType(context, instObj, op)

		return self.canonical.pathType(context.opPath, instObj, op)

	def process(self):
		while self.dirty:
			current = self.dirty.popleft()
			current.process(self)

	def createAssign(self, source, dest):
		con = AssignmentConstraint(source, dest)
		con.attach(self)
		return con

	def fold(self, targetcontext):
		def notConst(obj):
			return obj is util.cpa.Any or (obj is not None and not obj.obj.isConstant())

		sig = targetcontext.signature
		code = sig.code

		if code.annotation.dynamicFold:
			# It's foldable.
			p = code.codeparameters
			assert p.vparam is None, code.name
			assert p.kparam is None, code.name

			# TODO folding with constant vargs?
			# HACK the internal selfparam is usually not "constant" as it's a function, so we ignore it?
			#if notConst(sig.selfparam): return False
			for param in sig.params:
				if notConst(param): return False

			params = [param.obj for param in sig.params]
			result = foldFunctionIR(self.extractor, code.annotation.dynamicFold, params)
			resultxtype = self.canonical.existingType(result)

			# Set the return value
			assert len(p.returnparams) == 1
			name = self.canonical.localName(code, p.returnparams[0], targetcontext)
			returnSource = self.roots.root(self, name, self.roots.regionHint)
			returnSource.initializeType(self, resultxtype)

			return True

		return False

	def initializeContext(self, context):
		# Don't bother if the call can never happen.
		if context.invocationMaySucceed(self):
			# Caller-independant initalization.
			if context not in self.liveContexts:
				# Mark as initialized
				self.liveContexts.add(context)

				code = context.signature.code
				if code not in self.liveCode:
					# HACK convert the calls before analysis to eliminate UnpackTuple nodes.
					callConverter(self.extractor, code)
					self.liveCode.add(code)

				# Check to see if we can just fold it.
				# Dynamic folding only calculates the output,
				# so we still evaluate the constraints.
				folded = self.fold(context)

				# Extract the constraints
				exdf = ExtractDataflow(self, context, folded)
				exdf.process()
			return True
		return False

	def bindCall(self, cop, caller, targetcontext):
		assert isinstance(cop, base.OpContext), type(cop)

		sig = targetcontext.signature
		code = sig.code

		dst = self.canonical.codeContext(code, targetcontext)
		if dst not in self.opInvokes[cop]:
			# Record the invocation
			self.opInvokes[cop].add(dst)

			if self.initializeContext(targetcontext):
				targetcontext.bindParameters(self, caller)

	def addAttr(self, src, attrName, dst):
		srcxtype = self.canonical.externalType(src)
		fieldName = self.canonical.fieldName(*attrName)
		dstxtype = self.canonical.externalType(dst)

		obj = self.roots.regionHint.object(self, srcxtype)
		field = obj.field(self, fieldName, self.roots.regionHint)
		field.initializeType(self, dstxtype)

	def makeExternalSlot(self, name):
		code = base.externalFunction
		dummyLocal = ast.Local(name)
		dummyName = self.canonical.localName(code, dummyLocal, base.externalFunctionContext)
		dummySlot = self.roots.root(self, dummyName, self.roots.regionHint)
		return dummySlot

	def createEntryOp(self, entryPoint):
		# Make sure each op is unique.
		op = util.canonical.Sentinel('entry point op')
		cop = self.canonical.opContext(base.externalFunction, op, base.externalFunctionContext)
		self.entryPointOp[entryPoint] = cop
		return cop

	def getExistingSlot(self, pyobj):
		obj = self.extractor.getObject(pyobj)
		slot = self.makeExternalSlot('dummy_exist')
		argxtype = self.canonical.existingType(obj)
		slot.initializeType(self, argxtype)
		return slot


	def getInstanceSlot(self, typeobj):
		obj = self.extractor.getInstance(typeobj)
		slot = self.makeExternalSlot('dummy_inst')
		argxtype = self.canonical.externalType(obj)
		slot.initializeType(self, argxtype)
		return slot

	def getReturnSlot(self, ep):
		if ep not in self.entryPointReturn:
			self.entryPointReturn[ep] = self.makeExternalSlot('return_%s' % ep.name())
		return self.entryPointReturn[ep]

	def addEntryPoint(self, entryPoint):
		# The call point
		cop = self.createEntryOp(entryPoint)

		selfSlot = entryPoint.selfarg.get(self)
		argSlots = [arg.get(self) for arg in entryPoint.args]
		kwds = []
		varg = entryPoint.varg.get(self)
		karg = entryPoint.karg.get(self)
		returnSlots = [self.getReturnSlot(entryPoint)]

		# Create the initial constraint
		con = DirectCallConstraint(cop, entryPoint.code, selfSlot, argSlots, kwds, varg, karg, returnSlots)
		con.attach(self) # TODO move inside constructor?


	def solve(self):
		start = time.clock()
		# Process
		self.process()

		end = time.clock()

		self.solveTime = end-start-self.decompileTime


	### Annotation methods ###

	def collectContexts(self, lut, contexts):
		cdata  = [annotations.annotationSet(lut[context]) for context in contexts]
		return annotations.makeContextualAnnotation(cdata)

	def collectRMA(self, code, op):
		contexts = code.annotation.contexts

		creads     = [annotations.annotationSet(self.opReads[(code, op, context)]) for context in contexts]
		reads     = annotations.makeContextualAnnotation(creads)

		cmodifies  = [annotations.annotationSet(self.opModifies[(code, op, context)]) for context in contexts]
		modifies  = annotations.makeContextualAnnotation(cmodifies)

		callocates = [annotations.annotationSet(self.opAllocates[(code, op, context)]) for context in contexts]
		allocates = annotations.makeContextualAnnotation(callocates)

		return reads, modifies, allocates

	def annotateCode(self, code, contexts):
		code.rewriteAnnotation(contexts=tuple(contexts))

		# Creating vparam and kparam objects produces side effects...
		# Store them in the code annotation
		reads, modifies, allocates = self.collectRMA(code, None)
		code.rewriteAnnotation(codeReads=reads, codeModifies=modifies, codeAllocates=allocates)

	def mergeAbstractCode(self, code):
		# This is done after the ops and locals are annotated as the "abstractReads", etc. may depends on the annotations.
		reads     = annotations.mergeContextualAnnotation(code.annotation.codeReads, code.abstractReads())
		modifies  = annotations.mergeContextualAnnotation(code.annotation.codeModifies, code.abstractModifies())
		allocates = annotations.mergeContextualAnnotation(code.annotation.codeAllocates, code.abstractAllocates())

		code.rewriteAnnotation(codeReads=reads, codeModifies=modifies, codeAllocates=allocates)

	def reindexAnnotations(self):
		# Find the contexts that a given entrypoint invokes
		for entryPoint, op in self.entryPointOp.iteritems():
			contexts = [ccontext.context for ccontext in self.opInvokes[op]]
			entryPoint.contexts = contexts

		# Re-index the invocations
		invokeLUT = collections.defaultdict(lambda: collections.defaultdict(set))
		for srcop, dsts in self.opInvokes.iteritems():
			for dst in dsts:
				invokeLUT[(srcop.code, srcop.op)][srcop.context].add((dst.code, dst.context))

		# Re-index the locals
		lclLUT = collections.defaultdict(lambda: collections.defaultdict(set))
		for slot in self.roots:
			name = slot.slotName
			if name.isLocal():
				lclLUT[(name.code, name.local)][name.context] = slot
			elif name.isExisting():
				lclLUT[(name.code, name.object)][name.context] = slot

		return invokeLUT, lclLUT

	def annotate(self):
		invokeLUT, lclLUT = self.reindexAnnotations()

		for code, contexts in self.codeContexts.iteritems():
			self.annotateCode(code, contexts)

			contexts = code.annotation.contexts
			ops, lcls = getOps(code)

			for op in ops:
				invokes = self.collectContexts(invokeLUT[(code, op)], contexts)
				reads, modifies, allocates = self.collectRMA(code, op)

				op.rewriteAnnotation(
					invokes=invokes,
					opReads=reads,
					opModifies=modifies,
					opAllocates=allocates,
					)

			for lcl in lcls:
				if isinstance(lcl, ast.Existing):
					contextLclLUT = lclLUT[(code, lcl.object)]
				else:
					contextLclLUT = lclLUT[(code, lcl)]

				references = self.collectContexts(contextLclLUT, contexts)
				lcl.rewriteAnnotation(references=references)

			self.mergeAbstractCode(code)

	### Debugging methods ###

	def checkConstraints(self):
		badConstraints = []
		allBad = set()
		allWrite = set()
		for c in self.constraints:
			bad = c.getBad()
			if bad:
				badConstraints.append((c, bad))
				allBad.update(bad)
				allWrite.update(c.writes())

		# Try to find the constraints that started the problem.
		for c, bad in badConstraints:
			if not allWrite.issuperset(bad):
				c.check(self.console)



	def slotMemory(self):
		return self.setManager.memory()

def evaluate(console, extractor, interface, opPathLength=0, firstPass=True):
	dataflow = InterproceduralDataflow(console, extractor, opPathLength)
	dataflow.firstPass = firstPass # HACK for debugging

	# HACK
	base.externalFunctionContext.opPath = dataflow.initalOpPath()

	for src, attrName, dst in interface.attr:
		dataflow.addAttr(src, attrName, dst)

	for entryPoint in interface.entryPoint:
		dataflow.addEntryPoint(entryPoint)

	try:
		dataflow.solve()
		dataflow.checkConstraints()
	finally:
		dataflow.annotate()
		# HACK?
		dataflow.db.load(dataflow)

	return dataflow
