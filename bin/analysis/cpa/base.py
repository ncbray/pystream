from programIR.python import program, ast

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
		name = sys.canonical.localName(code, lcl, context)
		return sys.slotManager.root(sys, name, sys.slotManager.region)
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
	__slots__ = 'signature', 'opPath', 'group'

	def __init__(self, signature, opPath, group):
		self.signature = signature
		self.opPath    = opPath
		self.group     = group
		self.setCanonical(self.signature, self.opPath)

	def _bindObjToSlot(self, sys, obj, slot):
		assert not ((obj is None) ^ (slot is None)), (obj, slot)
		if obj is not None and slot is not None:
			assert isinstance(obj, extendedtypes.ExtendedType), type(obj)
			assert isinstance(slot, storegraph.SlotNode)

			slot.initializeType(sys, obj)

	def vparamType(self, sys):
		return self._extendedParamType(sys, sys.tupleClass.typeinfo.abstractInstance)

	def _extendedParamType(self, sys, inst):
		# Extended param objects are named by the context they appear in.
		return sys.canonical.signatureType(self.signature, inst)

	def _setVParamLength(self, sys, vparamObj, length):
		context = self

		# Set the length of the vparam tuple.
		slotName   = sys.lengthSlotName
		lengthObjxtype  = sys.canonical.existingType(sys.extractor.getObject(length))

		lengthSlot = vparamObj.field(sys, slotName, sys.slotManager.region)

		self._bindObjToSlot(sys, lengthObjxtype, lengthSlot)

	def _bindVParamIndex(self, sys, vparamObj, index, obj):
		context = self
		slotName = sys.canonical.fieldName('Array', sys.extractor.getObject(index))
		field = vparamObj.field(sys, slotName, sys.slotManager.region)
		self._bindObjToSlot(sys, obj, field)

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
			vparamType = self.vparamType(sys)
			self._bindObjToSlot(sys, vparamType, callee.vparam)
			sys.logAllocation(cop, vparamType) # Implicitly allocated

			# Set the length
			vparamObj = callee.vparam.knownObject(vparamType)
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
externalFunctionContext = AnalysisContext(externalSignature, None, None)


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