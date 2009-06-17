import collections
import itertools
import util

import base

from analysis.storegraph import storegraph, canonicalobjects, extendedtypes

from constraintextractor import ExtractDataflow

from constraints import AssignmentConstraint, DirectCallConstraint

# Only used for creating return variables
from language.python import ast
from language.python import program
from language.python import annotations

from optimization.callconverter import callConverter

from util.fold import foldFunction

from analysis.astcollector import getOps

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

class InterproceduralDataflow(object):
	def __init__(self, console, extractor, opPathLength=0):
		self.decompileTime = 0
		self.console   = console
		self.extractor = extractor

		# Has the context been constructed?
		self.liveContexts = set()

		self.liveCode = set()

		# Constraint information, for debugging
		self.constraints = set()

		# The worklist
		self.dirty = collections.deque()

		self.canonical = canonicalobjects.CanonicalObjects()
		self._canonicalContext = util.canonical.CanonicalCache(base.AnalysisContext)

		# Controls how many previous ops are remembered by a context.
		# TODO remember prior CPA signatures?
		self.opPathLength = opPathLength
		self.cache = {}

		# Information for contextual operations.
		self.opAllocates      = collections.defaultdict(set)
		self.opReads          = collections.defaultdict(set)
		self.opModifies       = collections.defaultdict(set)
		self.opInvokes        = collections.defaultdict(set)

		self.codeContexts     = collections.defaultdict(set)

		self.storeGraph = storegraph.StoreGraph(self.extractor, self.canonical)

		# Setup the "external" context, used for creaing bogus slots.
		self.externalOp  = util.canonical.Sentinel('<externalOp>')

		self.externalFunction = ast.Code('external', ast.CodeParameters(None, [], [], None, None, [ast.Local('internal_return')]), ast.Suite([]))
		externalSignature = self._signature(self.externalFunction, None, ())
		opPath  = self.initialOpPath()
		self.externalFunctionContext = self._canonicalContext(externalSignature, opPath, self.storeGraph)
		self.codeContexts[self.externalFunction].add(self.externalFunctionContext)


		# For vargs
		self.tupleClass = self.extractor.getObject(tuple)
		self.ensureLoaded(self.tupleClass)

		# For kargs
		self.dictionaryClass = self.extractor.getObject(dict)
		self.ensureLoaded(self.dictionaryClass)

		self.entryPointOp = {}
		self.entryPointReturn = {}

	def initialOpPath(self):
		if self.opPathLength == 0:
			path = None
		elif self.opPathLength == 1:
			path = self.externalOp
		else:
			path = (self.externalOp,)*self.opPathLength

		return self.cache.setdefault(path, path)

	def advanceOpPath(self, original, op):
		assert not isinstance(op, canonicalobjects.OpContext)

		if self.opPathLength == 0:
			path = None
		elif self.opPathLength == 1:
			path = op
		else:
			path = original[1:]+(op,)

		return self.cache.setdefault(path, path)
	def ensureLoaded(self, obj):
		# TODO the timing is no longer guarenteed, as the store graph bypasses this...
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
		assert code.isCode(), type(code)
		assert selfparam is None or selfparam is util.cpa.Any or isinstance(selfparam,  extendedtypes.ExtendedType), selfparam
		for param in params:
			assert param is util.cpa.Any or isinstance(param, extendedtypes.ExtendedType), param

		return util.cpa.CPASignature(code, selfparam, params)

	def canonicalContext(self, srcOp, code, selfparam, params):
		assert isinstance(srcOp, canonicalobjects.OpContext), type(srcOp)
		assert code.isCode(), type(code)

		sig     = self._signature(code, selfparam, params)
		opPath  = self.advanceOpPath(srcOp.context.opPath, srcOp.op)
		context = self._canonicalContext(sig, opPath, self.storeGraph)

		# Mark that we created the context.
		self.codeContexts[code].add(context)

		return context

	# This is the policy that determines what names a given allocation gets.
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
			current.process()

	def createAssign(self, source, dest):
		AssignmentConstraint(self, source, dest)

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
			returnSource = self.storeGraph.root(name)
			returnSource.initializeType(resultxtype)

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
		assert isinstance(cop, canonicalobjects.OpContext), type(cop)

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

		obj = self.storeGraph.regionHint.object(srcxtype)
		field = obj.field(fieldName, self.storeGraph.regionHint)
		field.initializeType(dstxtype)

	def makeExternalSlot(self, name):
		code    = self.externalFunction
		context = self.externalFunctionContext
		dummyLocal = ast.Local(name)
		dummyName = self.canonical.localName(code, dummyLocal, context)
		dummySlot = self.storeGraph.root(dummyName)
		return dummySlot

	def createEntryOp(self, entryPoint):
		code    = self.externalFunction
		context = self.externalFunctionContext

		# Make sure each op is unique.
		op = util.canonical.Sentinel('entry point op')
		cop = self.canonical.opContext(code, op, context)
		self.entryPointOp[entryPoint] = cop
		return cop

	def getExistingSlot(self, pyobj):
		obj  = self.extractor.getObject(pyobj)
		slot = self.makeExternalSlot('dummy_exist')
		slot.initializeType(self.canonical.existingType(obj))
		return slot

	def getInstanceSlot(self, typeobj):
		obj = self.extractor.getInstance(typeobj)
		slot = self.makeExternalSlot('dummy_inst')
		slot.initializeType(self.canonical.externalType(obj))
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
		DirectCallConstraint(self, cop, entryPoint.code, selfSlot, argSlots, kwds, varg, karg, returnSlots)


	def solve(self):
		start = time.clock()
		# Process
		self.process()

		end = time.clock()

		self.solveTime = end-start-self.decompileTime


	### Annotation methods ###

	def collectContexts(self, lut, contexts):
		cdata  = [annotations.annotationSet(lut[context]) for context in contexts]
		data = annotations.makeContextualAnnotation(cdata)

		data = self.annotationCache.setdefault(data, data)
		self.annotationCount += 1

		return data

	def collectRMA(self, code, op):
		contexts = code.annotation.contexts

		creads     = [annotations.annotationSet(self.opReads[(code, op, context)]) for context in contexts]
		reads     = annotations.makeContextualAnnotation(creads)

		cmodifies  = [annotations.annotationSet(self.opModifies[(code, op, context)]) for context in contexts]
		modifies  = annotations.makeContextualAnnotation(cmodifies)

		callocates = [annotations.annotationSet(self.opAllocates[(code, op, context)]) for context in contexts]
		allocates = annotations.makeContextualAnnotation(callocates)

		reads     = self.annotationCache.setdefault(reads, reads)
		modifies  = self.annotationCache.setdefault(modifies, modifies)
		allocates = self.annotationCache.setdefault(allocates, allocates)
		self.annotationCount += 3

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

		reads     = self.annotationCache.setdefault(reads, reads)
		modifies  = self.annotationCache.setdefault(modifies, modifies)
		allocates = self.annotationCache.setdefault(allocates, allocates)
		self.annotationCount += 3

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
		for slot in self.storeGraph:
			name = slot.slotName
			if name.isLocal():
				lclLUT[(name.code, name.local)][name.context] = slot
			elif name.isExisting():
				lclLUT[(name.code, name.object)][name.context] = slot

		return invokeLUT, lclLUT

	def annotate(self):
		self.annotationCount = 0
		self.annotationCache = {}

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

		self.console.output("Annotation compression %f - %d" % (float(len(self.annotationCache))/max(self.annotationCount, 1), self.annotationCount))

		del self.annotationCache
		del self.annotationCount

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
		return self.storeGraph.setManager.memory()

def evaluate(compiler, opPathLength=0, firstPass=True):
	dataflow = InterproceduralDataflow(compiler.console, compiler.extractor, opPathLength)
	dataflow.firstPass = firstPass # HACK for debugging

	for src, attrName, dst in compiler.interface.attr:
		dataflow.addAttr(src, attrName, dst)

	for entryPoint in compiler.interface.entryPoint:
		dataflow.addEntryPoint(entryPoint)

	try:
		with compiler.console.scope('solve'):
			dataflow.solve()
			dataflow.checkConstraints()
	finally:
		# Helps free up memory.
		with compiler.console.scope('cleanup'):
			dataflow.constraints.clear()
			dataflow.storeGraph.removeObservers()

		with compiler.console.scope('annotate'):
			dataflow.annotate()

		compiler.storeGraph = dataflow.storeGraph
		compiler.liveCode   = dataflow.liveCode

	return dataflow
