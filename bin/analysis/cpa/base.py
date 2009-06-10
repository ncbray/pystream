from language.python import program, ast

import util
import util.cpa
import util.calling
import util.canonical
CanonicalObject = util.canonical.CanonicalObject

from . import extendedtypes
from . import storegraph

###########################
### Evaluation Contexts ###
###########################

def localSlot(sys, code, lcl, context):
	if lcl:
		assert isinstance(lcl, ast.Local), type(lcl)
		name = sys.canonical.localName(code, lcl, context)
		return context.group.root(name)
	else:
		return None

def calleeSlotsFromContext(sys, context):
	code = context.signature.code

	callee = code.codeParameters()

	selfparam   = localSlot(sys, code, callee.selfparam, context)
	parameters  = tuple([localSlot(sys, code, p, context) for p in callee.params])
	defaults    = []
	vparam      = localSlot(sys, code, callee.vparam, context)
	kparam      = localSlot(sys, code, callee.kparam, context)
	returnparams = [localSlot(sys, code, param, context) for param in callee.returnparams]

	return util.calling.CalleeParams(selfparam, parameters,
		callee.paramnames, defaults, vparam, kparam, returnparams)


class AnalysisContext(CanonicalObject):
	__slots__ = 'signature', 'opPath', 'group'

	def __init__(self, signature, opPath, group):
		self.signature  = signature
		self.opPath     = opPath
		self.group      = group

		self.setCanonical(self.signature, self.opPath)

	def _bindObjToSlot(self, sys, obj, slot):
		assert not ((obj is None) ^ (slot is None)), (obj, slot)
		if obj is not None and slot is not None:
			assert isinstance(obj, extendedtypes.ExtendedType), type(obj)
			assert isinstance(slot, storegraph.SlotNode)

			slot.initializeType(obj)

	def vparamType(self, sys):
		return self._extendedParamType(sys, sys.tupleClass.typeinfo.abstractInstance)

	def _extendedParamType(self, sys, inst):
		# Extended param objects are named by the context they appear in.
		return sys.canonical.contextType(self, inst, None)


	def _vparamSlot(self, sys, vparamObj, index):
		slotName = sys.canonical.fieldName('Array', sys.extractor.getObject(index))
		field = vparamObj.field(slotName, self.group.regionHint)
		return field

	def invocationMaySucceed(self, sys):
		sig = self.signature
		callee = calleeSlotsFromContext(sys, self)

		# info is not actually intrinsic to the context?
		info = util.calling.callStackToParamsInfo(callee,
			sig.selfparam is not None, sig.numParams(),
			False, 0, False)

		if info.willSucceed.maybeFalse():
			if info.willSucceed.mustBeFalse():
				print "Call to %r will always fail." % self.signature
			else:
				print "Call to %r may fail." % self.signature

		return info.willSucceed.maybeTrue()

	def initializeVParam(self, sys, cop, vparamSlot, length):
		vparamType = self.vparamType(sys)

		# Set the varg pointer
		# Ensures the object node is created.
		self._bindObjToSlot(sys, vparamType, vparamSlot)

		vparamObj = vparamSlot.initializeType(vparamType)
		sys.logAllocation(cop, vparamObj) # Implicitly allocated

		# Set the length of the vparam tuple.
		lengthObjxtype  = sys.canonical.existingType(sys.extractor.getObject(length))
		lengthSlot = vparamObj.field(sys.lengthSlotName, self.group.regionHint)
		self._bindObjToSlot(sys, lengthObjxtype, lengthSlot)
		sys.logModify(cop, lengthSlot)

		return vparamObj


	def initalizeParameter(self, sys, param, cpaType, arg):
		if param is None:
			assert cpaType is None
			assert arg is None
		elif cpaType is util.cpa.Any:
			assert isinstance(param, storegraph.SlotNode)
			assert isinstance(arg,   storegraph.SlotNode)
			sys.createAssign(arg, param)
		else:
			# TODO skip this if this context has already been bound
			# but for a different caller
			param.initializeType(cpaType)


	def bindParameters(self, sys, caller):
		sig = self.signature

		callee = calleeSlotsFromContext(sys, self)

		# Bind self parameter
		self.initalizeParameter(sys, callee.selfparam, sig.selfparam, caller.selfarg)

		# Bind the positional parameters
		numArgs  = len(sig.params)
		numParam = len(callee.params)
		assert numArgs >= numParam
		for arg, cpaType, param in zip(caller.args[:numParam], sig.params[:numParam], callee.params):
			self.initalizeParameter(sys, param, cpaType, arg)

		# An op context for implicit allocation
		cop = sys.canonical.opContext(sig.code, None, self)

		# Bind the vparams
		if callee.vparam is not None:
			vparamObj = self.initializeVParam(sys, cop, callee.vparam, numArgs-numParam)

			# Bind the vargs
			for i in range(numParam, numArgs):
				arg     = caller.args[i]
				cpaType = sig.params[i]
				param = self._vparamSlot(sys, vparamObj, i-numParam)
				self.initalizeParameter(sys, param, cpaType, arg)
				sys.logModify(cop, param)

		else:
			assert numArgs == numParam

		# Bind the kparams
		assert callee.kparam is None


		# Copy the return value
		if caller.returnargs is not None:
			assert len(callee.returnparams) == len(caller.returnargs)
			for param, arg in zip(callee.returnparams, caller.returnargs):
				sys.createAssign(param, arg)

# Objects for external calls.

externalFunction = ast.Code('external', ast.CodeParameters(None, [], [], None, None, [ast.Local('internal_return')]), ast.Suite([]))
externalSignature = util.cpa.CPASignature(externalFunction, None, ())
externalFunctionContext = AnalysisContext(externalSignature, None, None)


class OpContext(CanonicalObject):
	__slots__ ='code', 'op', 'context',
	def __init__(self, code, op, context):
		assert code.isAbstractCode(), type(code)
		assert isinstance(context, AnalysisContext), context

		self.setCanonical(code, op, context)

		self.code     = code
		self.op       = op
		self.context  = context


class CodeContext(CanonicalObject):
	__slots__ = 'code', 'context',
	def __init__(self, code, context):
		assert code.isAbstractCode(), type(code)
		assert isinstance(context, AnalysisContext), context

		self.setCanonical(code, context)

		self.code     = code
		self.context  = context

	def decontextualize(self):
		return self.code