from programIR.python import program, ast

import util
import util.calling

import util.canonical
CanonicalObject = util.canonical.CanonicalObject

###########################
### Evaluation Contexts ###
###########################

class ObjectContext(CanonicalObject):
	__slots__ = ()

class AnalysisContext(CanonicalObject):
	__slots__ = ()

class CallPath(ObjectContext):
	__slots__ = 'path'
	
	def __init__(self, op, oldpath=None):
		if oldpath is None:
			# 6 seems to be the minimum?
			self.path = (None,)*8+(op,)
		else:
			self.path = oldpath.path[1:]+(op,)

		self.setCanonical(*self.path)

	def __repr__(self):
		#return "callpath(%s)" % ", ".join([str(id(op)) for op in self.path])
		return "callpath(%s)" % ", ".join([type(op).__name__+"/"+str(id(op)) for op in self.path])

	def advance(self, op):
		return CallPath(op, self)



class CPAContext(AnalysisContext):
	__slots__ = 'path', 'func', 'selfparam', 'params', 'vparams', 'vparamObj', 'kparamObj', 'callee', 'info'

	def __init__(self, path, func, selfparam, params, vparams, vparamObj, kparamObj):
		assert not isinstance(func, (AbstractSlot, ContextObject)), func
		assert selfparam is None or isinstance(selfparam, ContextObject), selfparam

		for param in params:
			assert isinstance(param, ContextObject), param
			
		for param in vparams:
			assert isinstance(param, ContextObject), param


		self.path  = path
		self.func  = func
		
		self.selfparam = selfparam
		self.params  = tuple(params)
		self.vparams = tuple(vparams)
		
		self.vparamObj = vparamObj
		self.kparamObj = kparamObj

		self.callee = util.calling.CalleeParams.fromFunction(func)
		self.info   = util.calling.callStackToParamsInfo(self.callee, len(params)+len(vparams), False, 0, False)

		if not self.info.willAlwaysSucceed:
			if self.info.willAlwaysFail:
				print "Call will always fail."
			else:
				print "Call may fail."
			print self.func.name
			print self.args
			print

		# Note that the vargObj and kargObj are considered to be "derived values"
		# (although they are created externally, as they require access to the system)
		# and as such aren't part of the hash or equality computations.
		self.setCanonical(self.path, self.func, self.selfparam, self.params, self.vparams)

	def __repr__(self):
		return "%s(%r, %r, %r, %r, %r)" % (type(self).__name__, self.path, self.func.name, self.selfparam, self.params, self.vparams)

	def bindParameters(self, sys):
		func = self.func
		context = self

		def bindObjToLocal(obj, lcl):
			if obj is not None and lcl is not None:
				sys.update(sys.canonical.local(context, func, lcl), (obj,))
		
		# Local binding done after creating constraints,
		# to ensure the variables are dirty.
		bindObjToLocal(context.selfparam,   func.code.selfparam)


		assert len(context.params) == len(func.code.parameters)
		for arg, param in zip(self.params, func.code.parameters):
			bindObjToLocal(arg, param)

		bindObjToLocal(context.vparamObj, func.code.vparam)
		bindObjToLocal(context.kparamObj, func.code.kparam)


		if context.vparamObj is not None:
			# Bind the vargs
			for i, param in enumerate(self.vparams):
				index = sys.extractor.getObject(i)
				target = sys.canonical.objectSlot(context.vparamObj, 'Array', sys.existingObject(index).obj)
				sys.update(target, (param,))


			# Set the length of the vparam tuple.
			length     = sys.existingObject(sys.extractor.getObject(len(self.vparams)))
			lengthStr  = sys.extractor.getObject('length')
			lengthSlot = sys.canonical.objectSlot(context.vparamObj, 'LowLevel', sys.existingObject(lengthStr).obj)
			sys.update(lengthSlot, (length,)) 


externalFunction = ast.Function('external', ast.Code(None, [], [], None, None, ast.Local('internal_return'), ast.Suite([])))

class ExternalFunctionContext(AnalysisContext):
	__slots__ = ()
		
externalFunctionContext = ExternalFunctionContext()

class ExternalOp(object):
	__slots__ = '__weakref__'
		
externalOp = ExternalOp()

class ExternalObjectContext(ObjectContext):
	__slots__ = ()

		
externalObjectContext = ExternalObjectContext()


class ExistingObjectContext(ObjectContext):
	__slots__ = ()

	def __repr__(self):
		return "%s()" % (type(self).__name__)

existingObjectContext = ExistingObjectContext()


##################
### Heap Names ###
##################

class ContextObject(CanonicalObject):
	__slots__ = 'context', 'obj'

	
	def __init__(self, context, obj):
		assert isinstance(context, ObjectContext), context
		assert isinstance(obj, program.AbstractObject), obj

		self.setCanonical(context, obj)
		
		self.context 	= context
		self.obj 	= obj

	def __repr__(self):
		return "%s(%r, %r)" % (type(self).__name__, id(self.context), self.obj)

	def decontextualize(self):
		return self.obj


class ContextOp(CanonicalObject):
	__slots__ = 'context', 'function', 'op'
	def __init__(self, context, function, op):
		assert isinstance(context, AnalysisContext), context
		assert isinstance(function, ast.Function), function
		#assert ast.isPythonAST(op), op

		self.setCanonical(context, function, op)

		self.context  = context
		self.function = function
		self.op       = op
		

class ContextFunction(CanonicalObject):
	__slots__ = 'context', 'function'
	def __init__(self, context, function):
		assert isinstance(context, AnalysisContext), context
		assert isinstance(function, ast.Function), function

		self.setCanonical(context, function)
		
		self.context  = context
		self.function = function

	def decontextualize(self):
		return self.function


##################
### Slot Names ###
##################

class AbstractSlot(CanonicalObject):
	__slots__ = ()
	
	def isLocalSlot(self):
		return False

	def isObjectSlot(self):
		return False

class ObjectSlot(AbstractSlot):
	__slots__ = 'obj', 'slottype', 'key', 'hash'
	
	def __init__(self, obj, slottype, key):
		assert isinstance(obj, ContextObject), obj
		assert isinstance(slottype, str)
		assert isinstance(key, program.AbstractObject), key

		self.setCanonical(obj, slottype, key)

		self.obj      = obj
		self.slottype = slottype
		self.key      = key

	def isObjectSlot(self):
		return True

	def createInital(self, sys):
		extractor = sys.extractor

		obj = self.obj.obj
		slottype = self.slottype
		key = self.key

		extractor.ensureLoaded(obj)

		# HACK Make sure it's canonical?  Shouldn't need to do this?
		# There must be a raw Object reference in the LLAst?
		key = extractor.getObject(key.pyobj)

		assert isinstance(obj, program.AbstractObject), obj
		assert isinstance(key, program.AbstractObject), key

		if isinstance(obj, program.Object):
			if slottype == 'LowLevel':
				subdict = obj.lowlevel
			elif slottype == 'Attribute':
				subdict = obj.slot
			elif slottype == 'Array':
				subdict = obj.array
			elif slottype == 'Dictionary':
				subdict = obj.dictionary
			else:
				assert False, slottype

			if key in subdict:
				result = set([sys.existingObject(subdict[key])])
			else:
				#print "Unknown slot: ", obj, slottype, key
				result = set()
		else:
			result = set()
		
		return result

class LocalSlot(AbstractSlot):
	__slots__ = 'context', 'function', 'local', 'hash'
	
	def __init__(self, context, function, local):
		self.setCanonical(context, function, local)
		
		self.context  = context
		self.function = function
		self.local    = local

	def isLocalSlot(self):
		return True
	
	def __repr__(self):
		return "%s(%d, %r, %r)" % (type(self).__name__, id(self.context), self.function.name, self.local)

	def createInital(self, sys):
		return set()


class CanonicalObjects(object):
	def __init__(self):
		self.local             = util.canonical.CanonicalCache(LocalSlot)
		self.objectSlot        = util.canonical.CanonicalCache(ObjectSlot)
		self.contextObject     = util.canonical.CanonicalCache(ContextObject)
		self._canonicalContext = util.canonical.CanonicalCache(CPAContext)
		self.contextOp         = util.canonical.CanonicalCache(ContextOp)
		self.contextFunction   = util.canonical.CanonicalCache(ContextFunction)

	def externalObject(self, obj):
		return self.contextObject(externalObjectContext, obj)

	def existingObject(self, obj):
		return self.contextObject(existingObjectContext, obj)

