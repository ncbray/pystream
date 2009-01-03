import collections

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




class Canonical(object):
	def __init__(self, create):
		self.create = create
		self.cache = {}

	def __call__(self, *args):
		obj = self.create(*args)
		if not obj in self.cache:
			self.cache[obj] = obj
			return obj
		else:
			return self.cache[obj]


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

		self.local             = Canonical(LocalSlot)
		self.objectSlot        = Canonical(ObjectSlot)
		self._contextObject     = Canonical(ContextObject)
		self._canonicalContext = Canonical(CPAContext)
		self.contextOp         = Canonical(ContextOp)
		self.contextFunction   = Canonical(ContextFunction)

		self.invocations = set()
		self.allocations = set()
		
		self.contextReads    = set()
		self.contextModifies = set()


		# Information for contextual operations.
		self.opReads         = collections.defaultdict(set)
		self.opModifies      = collections.defaultdict(set)
		self.opAllocates     = collections.defaultdict(set)
		self.opInvokes       = collections.defaultdict(set)

		self.functionContexts = collections.defaultdict(set)
		self.heapContexts = collections.defaultdict(set)

		self.rootPath = CallPath(None)

		self.entryPointDescs = []


		self.db = CPADatabase()

	def dependsRead(self, constraint, slot):
		self.reads[slot].add(constraint)
		if self.read(slot):
			constraint.mark(self)

	def canonicalContext(self, path, func, selfparam, params, vparams):
		# Create tuple for vparam
		if func.code.vparam is not None:
			tup = self.extractor.getObject(tuple)
			self.extractor.ensureLoaded(tup)

			# HACK should name per-context, rather than per-path, to maintain precision?
			# TODO create this inside the context?
			vparamObj = self.allocatedObject(path, tup.typeinfo.abstractInstance)


			# Make sure there's a type pointer...
			self.setTypePointer(vparamObj, self.existingObject(tup))
		else:
			vparamObj = None

		# Create dictionary for karg (disabled)
		assert func.code.kparam is None
		kparamObj = None
		
		context = self._canonicalContext(path, func, selfparam, params, vparams, vparamObj, kparamObj)
		self.functionContexts[func].add(context)
		return context

	def contextObject(self, context, obj):
		cobj = self._contextObject(context, obj)
		self.heapContexts[obj].add(context)
		return cobj
	
	def externalObject(self, obj):
		cobj = self.contextObject(externalObjectContext, obj)


		# HACK to initalize external objects.
		self.extractor.ensureLoaded(obj) # Makes sure the type pointer is valid.
		ctype = self.existingObject(obj.type)
		self.setTypePointer(cobj, ctype)
		return cobj

	def setTypePointer(self, obj, type_):		
		typestr = self.extractor.getObject('type')
		self.update(self.objectSlot(obj, 'LowLevel', typestr), (type_,))

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
		
		func = targetcontext.func
		
		if func in foldLUT:
			# It's foldable.

			# TODO folding with constant vargs?
			if notConst(targetcontext.selfparam): return False
			for param in targetcontext.params:
				if notConst(param): return False
			if notConst(targetcontext.vparamObj): return False
			if notConst(targetcontext.kparamObj): return False

			assert targetcontext.vparamObj is None, targetcontext.vparamObj
			assert targetcontext.kparamObj is None, targetcontext.kparamObj

			params = [param.obj for param in targetcontext.params]
			result = foldFunctionIR(self.extractor, foldLUT[func], params)
			result = self.existingObject(result)

			# Set the return value
			returnSource = self.local(targetcontext, func, func.code.returnparam)
			self.update(returnSource, (result,))
			
			return True

		return False

	# Only used to create an entry point.
	# TODO use util.calling and cpa iteration to break down the context.
	def getContext(self, path, func, funcobj, args):
		assert func is not None, funcObj

		funcobj = self.existingObject(funcobj)
		args    = [self.externalObject(arg) for arg in args]

		targetcontext = self.canonicalContext(path, func, funcobj, args, [])
		return targetcontext

	def bindCall(self, target, targetcontext):
			

		func = targetcontext.func


		info = self.db.functionInfo(func)
		info.descriptive = func in descriptiveLUT
		info.returnSlot = func.code.returnparam

		# Caller-spesific initalization
		# Done early, so constant folding makes the constraint dirty
		# Target may be done for the entrypoints.
		if target is not None:
			# Record the invocation			
			# HACK recoving op from callpath, may not work in the future.
			op = targetcontext.path.path[-1]

			sourceop = self.contextOp(target.context, target.function, op)
			dstfunc = self.contextFunction(targetcontext, func)
			
			self.invocations.add((sourceop, dstfunc))

			# Copy the return value
			returnSource = self.local(targetcontext, func, func.code.returnparam)
			self.createAssign(returnSource, target)


		# Caller-independant initalization.
		if not targetcontext in self.live:			
			self.live.add(targetcontext)
			
			if not self.fold(targetcontext):
				# Extract the constraints
				# Don't bother if the call can never happen.
				if not targetcontext.info.willAlwaysFail:
					exdf = ExtractDataflow(self, targetcontext, func)
					exdf(func)
					targetcontext.bindParameters(self)
		

	def addEntryPoint(self, func, funcobj, args):
		context = self.getContext(self.rootPath, func, funcobj, args)
		dummy = ast.Local('external_escape')
		dummyslot = self.local(externalFunctionContext, externalFunction, dummy)
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
