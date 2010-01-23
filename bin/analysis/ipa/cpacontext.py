import itertools

from util import canonical

from ..storegraph import extendedtypes

def cpaArgOK(arg):
	return arg is None or arg is anyType or isinstance(arg, extendedtypes.ExtendedType)

class CPAContextSignature(canonical.CanonicalObject):
	def __init__(self, code, selfparam, params, vparams):

		assert cpaArgOK(selfparam), selfparam
		for param in params:
			assert cpaArgOK(param), param
		for param in vparams:
			assert cpaArgOK(param), param

		self.code      = code
		self.selfparam = selfparam
		self.params    = params
		self.vparams   = vparams

		# Sanity check, probably a runaway loop in the analysis logic.
		assert len(vparams) < 30, code

		self.setCanonical(code, selfparam, params, vparams)

	def __repr__(self):
		return "cpa(%r, %r, %r, %r/%d)" % (self.code, self.selfparam, self.params, self.vparams, id(self))

anyType = object()
anyTypeIter = (anyType,)
nullIter = (None,)

class CPATypeSigBuilder(object):
	def __init__(self, analysis, call, info):
		self.analysis = analysis
		self.call = call

		self.code = self.call.code
		self.selfparam  = None
		self.params     = [None for i in range(info.numParams())]
		self.vparams    = [None for i in range(info.numVParams())]

		assert not info.numKParams()

	def unusedSelfParam(self):
		self.selfparam = nullIter

	def setSelfParam(self, value):
		self.selfparam = value

	def unusedParam(self, index):
		self.params[index] = nullIter

	def setParam(self, index, value):
		self.params[index] = value

	def unusedVParam(self, index):
		self.vparams[index] = nullIter

	def setVParam(self, index, value):
		self.vparams[index] = value

	def getSelfArg(self):
		return self.call.selfarg.typeSplit.types()

	def getArg(self, index):
		return self.call.args[index].typeSplit.types()

	def getVArg(self, index):
		return self.call.varg[index].typeSplit.types()


	def signatures(self):
		results = []
		for concrete in itertools.product(self.selfparam, *self.params+self.vparams):
			selfparam = concrete[0]
			params = concrete[1:len(self.params)+1]
			vparams = concrete[len(self.params)+1:]

			sig = CPAContextSignature(self.code, selfparam, params, vparams)
			sig = self.analysis.canonicalSignature(sig)

			results.append(sig)

		return results

externalContext = CPAContextSignature(None, None, (), ())
