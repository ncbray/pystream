from programIR.python import program, ast

import util
import util.cpa
import util.calling
import util.canonical
CanonicalObject = util.canonical.CanonicalObject

###########################
### Evaluation Contexts ###
###########################

def localSlot(sys, code, lcl, context):
	if lcl:
		return sys.canonical.local(code, lcl, context)
	else:
		return None

def calleeSlotsFromContext(sys, context):
	code = context.signature.code

	selfparam   = localSlot(sys, code, code.selfparam, context)
	parameters  = tuple([localSlot(sys, code, p, context) for p in code.parameters])
	defaults    = []
	vparam      = localSlot(sys, code, code.vparam, context)
	kparam      = localSlot(sys, code, code.kparam, context)
	returnparam = localSlot(sys, code, code.returnparam, context)

	return util.calling.CalleeParams(selfparam, parameters,
		code.parameternames, defaults, vparam, kparam, returnparam)


class AnalysisContext(CanonicalObject):
	__slots__ = 'signature', 'opPath'

	def __init__(self, signature, opPath):
		self.signature = signature
		self.opPath    = opPath
		self.setCanonical(self.signature, self.opPath)

	def _bindObjToSlot(self, sys, obj, slot):
		assert not ((obj is None) ^ (slot is None)), (obj, slot)
		if obj is not None and slot is not None:
			sys.update(slot, (obj,))

	def vparamObject(self, sys):
		return self._extendedParamObject(sys, sys.tupleClass.typeinfo.abstractInstance)

	def _extendedParamObject(self, sys, inst):
		# Extended param objects are named by the context they appear in.
		context = sys.canonical.signatureContext(self.signature)
		return sys.allocatedObject(context, inst)

	def _setVParamLength(self, sys, vparamObj, length):
		context = self

		# Set the length of the vparam tuple.
		lengthObj  = sys.existingObject(sys.extractor.getObject(length))
		lengthStr  = sys.extractor.getObject('length')
		lengthSlot = sys.canonical.objectSlot(vparamObj, 'LowLevel', sys.existingObject(lengthStr).obj)
		self._bindObjToSlot(sys, lengthObj, lengthSlot)

	def _bindVParamIndex(self, sys, vparamObj, index, obj):
		context = self
		index  = sys.extractor.getObject(index)
		slot = sys.canonical.objectSlot(vparamObj, 'Array', sys.existingObject(index).obj)
		self._bindObjToSlot(sys, obj, slot)

	def invocationMaySucceed(self, sys):
		sig = self.signature
		callee = calleeSlotsFromContext(sys, self)

		# info is not actually intrinsic to the context?
		info = util.calling.callStackToParamsInfo(callee,
			sig.selfparam is not None, sig.numParams(),
			False, 0, False)

		if info.willSucceed.maybeFalse():
			if info.willSucceed.mustBeFalse():
				print "Call to %s will always fail." % func.name
			else:
				print "Call to %s may fail." % func.name

		return info.willSucceed.maybeTrue()

	def bindParameters(self, sys):
		sig = self.signature

		callee = calleeSlotsFromContext(sys, self)

		# Bind self parameter
		self._bindObjToSlot(sys, sig.selfparam, callee.selfparam)

		# Bind the positional parameters
		numArgs  = len(sig.params)
		numParam = len(callee.params)
		assert numArgs >= numParam
		for arg, param in zip(sig.params[:numParam], callee.params):
			self._bindObjToSlot(sys, arg, param)

		# An op context for implicit allocation
		cop = sys.canonical.opContext(sig.code, None, self)

		# Bind the vparams
		if sig.code.vparam is not None:
			vparamObj = self.vparamObject(sys)
			sys.logAllocation(cop, vparamObj) # Implicitly allocated
			self._bindObjToSlot(sys, vparamObj, callee.vparam)
			self._setVParamLength(sys, vparamObj, numArgs-numParam)

			# Bind the vargs
			for i in range(numParam, numArgs):
				self._bindVParamIndex(sys, vparamObj, i-numParam, sig.params[i])
		else:
			assert numArgs == numParam

		# Bind the kparams
		assert sig.code.kparam is None


# Objects for external calls.
externalFunction = ast.Function('external', ast.Code('external', None, [], [], None, None, ast.Local('internal_return'), ast.Suite([])))
externalSignature = util.cpa.CPASignature(externalFunction.code, None, ())
externalFunctionContext = AnalysisContext(externalSignature, None)


######################
### Extended Types ###
######################

class ObjectContext(CanonicalObject):
	__slots__ = ()

class ExternalObjectContext(ObjectContext):
	__slots__ = ()

	def __repr__(self):
		return "<external>"

externalObjectContext = ExternalObjectContext()


class ExistingObjectContext(ObjectContext):
	__slots__ = ()

	def __repr__(self):
		return "<existing>"

existingObjectContext = ExistingObjectContext()


class PathObjectContext(ObjectContext):
	__slots__ = 'path',

	def __init__(self, path):
		self.path = path
		self.setCanonical(path)

	def __repr__(self):
		return "<path %d>" % id(self.path)

class MethodContext(ObjectContext):
	__slots__ = 'func', 'inst'

	def __init__(self, func, inst):
		self.func = func
		self.inst = inst
		self.setCanonical(func, inst)

	def __repr__(self):
		return "<method %d %d>" % (id(self.func), id(self.inst))

class SignatureContext(ObjectContext):
	__slots__ = 'sig'

	def __init__(self, sig):
		self.sig = sig
		self.setCanonical(sig)

	def __repr__(self):
		return "<sig %d>" % (id(self.sig),)

##################
### Heap Names ###
##################

class ContextObject(CanonicalObject):
	__slots__ = 'context', 'obj'


	def __init__(self, context, obj):
		assert isinstance(context, ObjectContext), context
		assert isinstance(obj, program.AbstractObject), repr(obj)

		self.setCanonical(context, obj)

		self.context 	= context
		self.obj 	= obj

	def __repr__(self):
		return "%s(%r, %r)" % (type(self).__name__, self.context, self.obj)

	def decontextualize(self):
		return self.obj


class OpContext(CanonicalObject):
	__slots__ ='code', 'op', 'context',
	def __init__(self, code, op, context):
		assert isinstance(code, ast.Code), code
		assert isinstance(context, AnalysisContext), context

		self.setCanonical(code, op, context)

		self.code     = code
		self.op       = op
		self.context  = context


class CodeContext(CanonicalObject):
	__slots__ = 'code', 'context',
	def __init__(self, code, context):
		assert isinstance(code, ast.Code), code
		assert isinstance(context, AnalysisContext), context

		self.setCanonical(code, context)

		self.code     = code
		self.context  = context

	def decontextualize(self):
		return self.code


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
		obj = self.obj.obj
		slottype = self.slottype
		key = self.key

		sys.ensureLoaded(obj)

		# HACK Make sure it's canonical?  Shouldn't need to do this?
		# There must be a raw Object reference in the LLAst?
		key = sys.extractor.getObject(key.pyobj)

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
	__slots__ = 'code', 'local', 'context'

	def __init__(self, code, local, context):
		assert isinstance(code,  ast.Code), code
		assert not isinstance(local, AbstractSlot), local # This is obviously bad...
		#assert isinstance(local, (ast.Local, program.Object, ast.Expression)), type(local) # HACK...
		assert isinstance(context, AnalysisContext), context

		self.setCanonical(code, local, context)

		self.code    = code
		self.local   = local
		self.context = context

	def isLocalSlot(self):
		return True

	def __repr__(self):
		return "%s(%r, %r, %d)" % (type(self).__name__, self.code.name, self.local, id(self.context))

	def createInital(self, sys):
		return set()


class CanonicalObjects(object):
	def __init__(self):
		self.local             = util.canonical.CanonicalCache(LocalSlot)
		self.objectSlot        = util.canonical.CanonicalCache(ObjectSlot)
		self.contextObject     = util.canonical.CanonicalCache(ContextObject)
		self._canonicalContext = util.canonical.CanonicalCache(AnalysisContext)
		self.opContext         = util.canonical.CanonicalCache(OpContext)
		self.codeContext       = util.canonical.CanonicalCache(CodeContext)

		self.cache = {}

	def externalObject(self, obj):
		return self.contextObject(externalObjectContext, obj)

	def existingObject(self, obj):
		return self.contextObject(existingObjectContext, obj)

	def path(self, old, op):
		new = old.advance(op)
		return self.cache.setdefault(new, new)

	def pathContext(self, path):
		new = PathObjectContext(path)
		return self.cache.setdefault(new, new)

	def methodContext(self, func, inst):
		new = MethodContext(func, inst)
		return self.cache.setdefault(new, new)

	def signatureContext(self, sig):
		new = SignatureContext(sig)
		return self.cache.setdefault(new, new)