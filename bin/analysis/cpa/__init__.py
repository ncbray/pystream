import collections
import itertools
import util

import base

from . import canonicalobjects
from . import extendedtypes
from . import setmanager

import dumpreport

from constraintextractor import ExtractDataflow

from constraints import AssignmentConstraint

# Only used for creating return variables
from programIR.python import ast
from programIR.python import program

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
	def __init__(self, console, extractor):
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
		self.opPathLength  = 0
		self.cache = {}

		# The storage graph
		self.roots  = storegraph.RegionGroup()

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
		self.opAllocates[cop].add(cobj)

	def logRead(self, cop, slot):
		assert isinstance(slot, storegraph.SlotNode), type(slot)
		self.opReads[cop].add(slot)

	def logModify(self, cop, slot):
		assert isinstance(slot, storegraph.SlotNode), type(slot)
		self.opModifies[cop].add(slot)

	def constraint(self, constraint):
		self.constraints.add(constraint)

	def _signature(self, code, selfparam, params):
		assert isinstance(code, ast.Code), type(code)
		#assert not isinstance(code, (AbstractSlot, extendedtypes.ExtendedType)), code
		assert selfparam is None or selfparam is util.cpa.Any or isinstance(selfparam,  extendedtypes.ExtendedType), selfparam
		for param in params:
			assert param is util.cpa.Any or isinstance(param, extendedtypes.ExtendedType), param

		return util.cpa.CPASignature(code, selfparam, params)

	def canonicalContext(self, srcOp, code, selfparam, params):
		assert isinstance(srcOp, base.OpContext), type(srcOp)
		assert isinstance(code, ast.Code), type(code)

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

	def extendedInstanceType(self, context, xtype):
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
				return self.canonical.methodType(func, inst, instObj)
		elif pyobj is types.TupleType or pyobj is types.ListType or pyobj is types.DictionaryType:
			# Containers are named by the signature of the context they're allocated in.
			return self.canonical.contextType(context, instObj)

		# Note: this path does not include the final op, which is this
		# allocate.  This is good as long as there is only one allocation
		# in a given context. (It makes better use of the finite path length.)
		return self.canonical.pathType(context.opPath, instObj)
		#return self.canonical.contextType(context, instObj)

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
			return obj is not None and not obj.obj.isConstant()

		sig = targetcontext.signature
		code = sig.code

		if code.annotation.dynamicFold:
			# It's foldable.
			assert code.vparam is None, code.name
			assert code.kparam is None, code.name

			# TODO folding with constant vargs?
			# HACK the internal selfparam is usually not "constant" as it's a function, so we ignore it?
			#if notConst(sig.selfparam): return False
			for param in sig.params:
				if notConst(param): return False

			params = [param.obj for param in sig.params]
			result = foldFunctionIR(self.extractor, code.annotation.dynamicFold, params)
			resultxtype = self.canonical.existingType(result)

			# Set the return value
			name = self.canonical.localName(code, code.returnparam, targetcontext)
			returnSource = self.roots.root(self, name, self.roots.regionHint)
			returnSource.initializeType(self, resultxtype)

			return True

		return False

	# Only used to create an entry point.
	# TODO use util.calling and cpa iteration to break down the context.
	def getContext(self, srcOp, code, funcobj, args):
		assert isinstance(code, ast.Code), type(code)

		funcobjxtype = self.canonical.existingType(funcobj)
		argxtypes    = tuple([self.canonical.externalType(arg) for arg in args])

		targetcontext = self.canonicalContext(srcOp, code, funcobjxtype, argxtypes)
		return targetcontext

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

	def makeExternalSlot(self, name):
		code = base.externalFunction
		dummyLocal = ast.Local(name)
		dummyName = self.canonical.localName(code, dummyLocal, base.externalFunctionContext)
		dummySlot = self.roots.root(self, dummyName, self.roots.regionHint)
		return dummySlot

	def addEntryPoint(self, func, funcobj, args):
		# The call point
		# TODO generate bogus ops?
		dummyOp = self.canonical.opContext(base.externalFunction, externalOp, base.externalFunctionContext)

		self.codeContexts[base.externalFunction].add(base.externalFunctionContext)

		funcobjxtype = self.canonical.existingType(funcobj)
		argxtypes    = tuple([self.canonical.externalType(arg) for arg in args])

		# Generate caller information
		selfSlot = self.makeExternalSlot('dummy_self')
		selfSlot.initializeType(self, funcobjxtype)

		argSlots = []
		for argxtype in argxtypes:
			argSlot = self.makeExternalSlot('dummy_param')
			argSlot.initializeType(self, argxtype)
			argSlots.append(argSlot)

		dummyReturnSlot = self.makeExternalSlot('dummy_return')

		caller = util.calling.CallerArgs(selfSlot, argSlots, [], None, None, dummyReturnSlot)


		# Generate the calling context
		context = self.getContext(dummyOp, func, funcobj, args)

		# Make an invocation
		self.bindCall(dummyOp, caller, context)

		context.entryPoint = True

	def solve(self):
		start = time.clock()
		# Process
		self.process()

		end = time.clock()

		self.solveTime = end-start-self.decompileTime

	def annotate(self):
		# Re-index the invocations
		opLut = collections.defaultdict(lambda: collections.defaultdict(set))
		for srcop, dsts in self.opInvokes.iteritems():
			for dst in dsts:
				opLut[(srcop.code, srcop.op)][srcop.context].add((dst.code, dst.context))


		# Re-index the locals
		lclLUT = collections.defaultdict(lambda: collections.defaultdict(set))
		for slot in self.roots:
			name = slot.slotName
			if name.isLocal():
				lclLUT[(name.code, name.local)][name.context] = slot

			# TODO existing?


		for code, contexts in self.codeContexts.iteritems():
			code.rewriteAnnotation(contexts=tuple(contexts))
			ops, lcls = getOps(code)

			for op in ops:
				if op is not externalOp:
					contextLUT = opLut[(code, op)]

					cinvokes = tuple([sorted(contextLUT[context]) for context in code.annotation.contexts])

					merged = set()
					for inv in cinvokes: merged.update(inv)

					op.rewriteAnnotation(invokes=(tuple(sorted(merged)), cinvokes))

			# TODO existing nodes?

			for lcl in lcls:
				contextLUT = lclLUT[(code, lcl)]
				crefs = tuple([sorted(contextLUT[context]) for context in code.annotation.contexts])

				merged = set()
				for refs in crefs: merged.update(refs)


				lcl.rewriteAnnotation(references=(tuple(sorted(merged)), crefs))



	def checkConstraints(self):
		for c in self.constraints:
			c.check(self.console)

	def slotMemory(self):
		return self.setManager.memory()

def evaluate(console, extractor, entryPoints):
	dataflow = InterproceduralDataflow(console, extractor)

	# HACK
	base.externalFunctionContext.opPath = dataflow.initalOpPath()

	for funcast, funcobj, args in entryPoints:
		assert isinstance(funcast, ast.Code), type(funcast)
		assert isinstance(funcobj, program.Object), type(funcobj)
		assert isinstance(args, (list, tuple)), type(args)
		dataflow.addEntryPoint(funcast, funcobj, args)

	dataflow.solve()
	dataflow.checkConstraints()
	dataflow.annotate()

	# HACK?
	dataflow.db.load(dataflow)

	return dataflow
