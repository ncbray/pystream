import collections

import util

from base import *

import dumpreport

from stubs.stubcollector import foldLUT

from constraintextractor import ExtractDataflow

from constraints import AssignmentConstraint

# Only used for creating return variables
from programIR.python import ast
from programIR.python import program

from util.fold import foldFunction


from . cpadatabase import CPADatabase

# HACK?
from stubs.stubcollector import descriptiveLUT

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
	def __init__(self, extractor):
		self.extractor = extractor

		self.functions = {}
		self.objects   = {}

		self.returnVariables = collections.defaultdict(lambda: ast.Local('return_value'))

		self.live = set()

		self.slots = {}
		self.reads  = collections.defaultdict(set)

		self.dirty = collections.deque()

		self.canonical = CanonicalObjects()

		self.invocations = set()
		self.allocations = set()

		self.contextReads    = set()
		self.contextModifies = set()


		# Information for contextual operations.
		self.opReads          = collections.defaultdict(set)
		self.opModifies       = collections.defaultdict(set)
		self.opInvokes        = collections.defaultdict(set)

		self.codeContexts = collections.defaultdict(set)
		self.heapContexts     = collections.defaultdict(set)

		self.rootPath = CallPath(None)

		self.entryPointDescs = []


		self.db = CPADatabase()
		self.db.canonical = self.canonical # HACK so the canonical objects are accessable.

		# For vargs
		self.tupleClass = self.extractor.getObject(tuple)
		self.extractor.ensureLoaded(self.tupleClass)

		# For kargs
		self.dictionaryClass = self.extractor.getObject(dict)
		self.extractor.ensureLoaded(self.dictionaryClass)

	def allocation(self, op, context, obj):
		self.allocations.add((context, obj))

	def dependsRead(self, constraint, slot):
		self.reads[slot].add(constraint)
		if self.read(slot):
			constraint.mark(self)

	def extendedParamObjects(self, code, path):
		if code.vparam is not None:
			# Create tuple for vparam
			# HACK should name per-context, rather than per-path, to maintain precision?
			# TODO create this inside the context w/opcode?
			vparamObj = self.allocatedObject(path, self.tupleClass.typeinfo.abstractInstance)
		else:
			vparamObj = None

		# Create dictionary for karg (disabled)
		assert code.kparam is None
		kparamObj = None

		return vparamObj, kparamObj

	def canonicalContext(self, code, path, selfparam, params, vparams):
		assert isinstance(code, ast.Code), type(code)
		vparamObj, kparamObj = self.extendedParamObjects(code, path)
		context = self.canonical._canonicalContext(code, path, selfparam, params, vparams, vparamObj, kparamObj)

		# Mark that we create the context.
		self.codeContexts[code].add(context)

		# Mark that we implicitly allocated these objects
		if vparamObj: self.allocation(None, context, vparamObj)
		if kparamObj: self.allocation(None, context, kparamObj)

		return context

	def setTypePointer(self, cobj):
		# Makes sure the type pointer is valid.
		typestr = self.extractor.getObject('type')
		slot    = self.canonical.objectSlot(cobj, 'LowLevel', typestr)

		if not self.read(slot):
			self.extractor.ensureLoaded(cobj.obj)
			type_ = self.existingObject(cobj.obj.type)
			self.update(slot, (type_,))

	def contextObject(self, context, obj):
		isNew = not self.canonical.contextObject.exists(context, obj)
		cobj  = self.canonical.contextObject(context, obj)
		if isNew:
			self.setTypePointer(cobj)
			self.heapContexts[obj].add(context)
		return cobj

	def externalObject(self, obj):
		return self.contextObject(externalObjectContext, obj)

	def existingObject(self, obj):
		return self.contextObject(existingObjectContext, obj)

	def allocatedObject(self, context, obj):
		return self.contextObject(context, obj)


	def process(self):
		while self.dirty:
			current = self.dirty.popleft()
			current.process(self)

	def read(self, slot):
		assert isinstance(slot, AbstractSlot), slot
		if not slot in self.slots:
			self.slots[slot] = slot.createInital(self)
		return self.slots[slot]

	def update(self, slot, values):
		assert isinstance(slot, AbstractSlot), slot
		for value in values:
			assert isinstance(value, ContextObject), value

		# If the slot is unitialized, pull the inital value from the heap.
		if not slot in self.slots:
			self.slots[slot] = slot.createInital(self)

		target = self.slots[slot]
		diff = set(values)-target
		if diff:
			self.slots[slot].update(diff)
			for dep in self.reads[slot]:
				dep.mark(self)


	def createAssign(self, source, dest):
		con = AssignmentConstraint(source, dest)
		con.attach(self)
		#con.mark(self)

	def fold(self, targetcontext):
		def notConst(obj):
			return obj is not None and not obj.obj.isConstant()

		sig = targetcontext.signature
		code = sig.code

		if code in foldLUT:
			# It's foldable.

			# TODO folding with constant vargs?
			# HACK the internal selfparam is usually not "constant" as it's a function, so we ignore it?
			#if notConst(sig.selfparam): return False
			for param in sig.params:
				if notConst(param): return False

			assert targetcontext.vparamObj is None, targetcontext.vparamObj
			assert targetcontext.kparamObj is None, targetcontext.kparamObj

			params = [param.obj for param in sig.params]
			result = foldFunctionIR(self.extractor, foldLUT[code], params)
			result = self.existingObject(result)

			# Set the return value
			returnSource = self.canonical.local(code, code.returnparam, targetcontext)
			self.update(returnSource, (result,))

			return True

		return False

	# Only used to create an entry point.
	# TODO use util.calling and cpa iteration to break down the context.
	def getContext(self, code, path, funcobj, args):
		assert isinstance(code, ast.Code), type(code)

		funcobj = self.existingObject(funcobj)
		args    = tuple([self.externalObject(arg) for arg in args])

		targetcontext = self.canonicalContext(code, path, funcobj, args, ())
		return targetcontext

	def bindCall(self, target, targetcontext):
		# HACK pulling context from target, and op from path.  Pass explicitly.

		sig = targetcontext.signature
		code = sig.code

		# HACK still called functionInfo
		info = self.db.functionInfo(code)
		info.descriptive = code in descriptiveLUT
		info.returnSlot  = code.returnparam

		# Caller-spesific initalization
		# Done early, so constant folding makes the constraint dirty
		# Target may be done for the entrypoints.
		if target is not None:
			# Record the invocation
			# HACK recoving op from callpath, may not work in the future.
			op = sig.path.path[-1]

			sourceop = self.canonical.opContext(target.code, op, target.context)
			dst      = self.canonical.codeContext(code, targetcontext)

			self.invocations.add((sourceop, dst))

			# Copy the return value
			returnSource = self.canonical.local(code, code.returnparam, targetcontext)
			self.createAssign(returnSource, target)


		# Caller-independant initalization.
		if not targetcontext in self.live:
			self.live.add(targetcontext)

			if not self.fold(targetcontext):
				# Extract the constraints
				# Don't bother if the call can never happen.
				if targetcontext.invocationMaySucceed(self):
					exdf = ExtractDataflow(self, code, targetcontext)
					exdf(code)
					targetcontext.bindParameters(self)


	def addEntryPoint(self, func, funcobj, args):
		context = self.getContext(func.code, self.rootPath, funcobj, args)
		dummy = ast.Local('external_escape')
		dummyslot = self.canonical.local(externalFunction.code, dummy, externalFunctionContext)
		self.bindCall(dummyslot, context)


	def solve(self):
		# Process
		self.process()


def evaluate(extractor, entryPoints):
	dataflow = InterproceduralDataflow(extractor)

	for funcast, funcobj, args in entryPoints:
		assert isinstance(funcast, ast.Function), type(funcast)
		assert isinstance(funcobj, program.Object), type(funcobj)
		assert isinstance(args, (list, tuple)), type(args)

		dataflow.addEntryPoint(funcast, funcobj, args)


	dataflow.solve()

	# HACK?
	dataflow.db.load(dataflow)

	return dataflow
