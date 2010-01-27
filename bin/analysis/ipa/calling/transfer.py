from util import tvl

class BaseArg(object):
	__slots__ = 'index',
	def __init__(self, index):
		self.index = index

class PositionalArg(BaseArg):
	__slots__ = ()
	def get(self, getter):
		return getter.getArg(self.index)

	def __repr__(self):
		return 'p(%d)' % self.index

class VariableArg(BaseArg):
	__slots__ = ()
	def get(self, getter):
		return getter.getVArg(self.index)

	def __repr__(self):
		return 'v(%d)' % self.index

class DefaultArg(BaseArg):
	__slots__ = ()
	def get(self, getter):
		return getter.getDefault(self.index)

	def __repr__(self):
		return 'd(%d)' % self.index


class TransferInfo(object):
	def __init__(self):
		self.selfparam  = False
		self.params     = []
		self.vparams    = []
		self.kparams    = []
		self.numReturns = 0
		self.transferOK = tvl.TVLTrue

	def transfer(self, getter, setter):
		if not self.selfparam:
			setter.unusedSelfParam()
		else:
			setter.setSelfParam(getter.getSelfArg())

		for i, p in enumerate(self.params):
			if p is None:
				setter.unusedParam(i)
			else:
				setter.setParam(i, p.get(getter))

		for i, p in enumerate(self.vparams):
			if p is None:
				setter.unusedVParam(i)
			else:
				setter.setVParam(i, p.get(getter))

		for kwd, p in enumerate(self.kparams):
			if p is None:
				setter.unusedKParam(kwd)
			else:
				setter.setKParam(kwd, p.get(getter))

		for i in range(self.numReturns):
			getter.setReturnArg(i, setter.getReturnParam(i))

	def invalidate(self):
		self.selfparam  = None
		self.params     = []
		self.vparams    = []
		self.kparams    = []
		self.transferOK = tvl.TVLFalse

	def maybeOK(self):
		return self.transferOK.maybeTrue()

	def numParams(self):
		return len(self.params)

	def numVParams(self):
		return len(self.vparams)

	def numKParams(self):
		return len(self.kparams)


class TransferInfoBuilder(object):
	def __init__(self):
		self.info = TransferInfo()
		self.argsConsumed  = 0
		self.vargsConsumed = 0

	def invalidateTransfer(self):
		self.info.invalidate()
		return self.info

	def argsRemain(self):
		return self.argsConsumed < self.arglen

	def vargsRemain(self):
		return self.vargsConsumed < self.varglen

	def getArg(self):
		arg = PositionalArg(self.argsConsumed)
		self.argsConsumed += 1
		return arg

	def getVArg(self):
		arg = VariableArg(self.vargsConsumed)
		self.vargsConsumed += 1
		return arg

	def positionalArgsRemain(self):
		return self.argsRemain() or self.vargsRemain()

	def getPositional(self):
		if self.argsRemain():
			return self.getArg()
		else:
			return self.getVArg()

	def defaultExists(self, index):
		return False

	def getDefault(self, index):
		return None

	def setParam(self, index, value):
		if self.cparams.params[index].isDoNotCare():
			value = None
		self.info.params.append(value)

	def setVParam(self, value):
		if self.cparams.vparam.isDoNotCare():
			# In theory it would be nice to collapse contexts with
			# different vparam lengths, but this could cause argument
			# normalization to be unsound.
			value = None
		self.info.vparams.append(value)

	def compute(self, code, selfarg, arglen, varglen, returnarglen):
		self.code    = code

		self.arglen  = arglen
		self.varglen = varglen

		cparams = code.codeParameters()
		self.cparams = cparams

		if cparams.selfparam is not None:
			if selfarg:
				self.info.selfparam = not cparams.selfparam.isDoNotCare()
			else:
				# Self arg is missing
				return self.invalidateTransfer()

		for i, param in enumerate(cparams.params):
			if self.positionalArgsRemain():
				self.setParam(i, self.getPositional())
			elif self.defaultExists(i):
				self.setParam(i, self.getDefault(i))
			else:
				# Not enough positional parameters
				return self.invalidateTransfer()

		if cparams.vparam is not None:
			while self.positionalArgsRemain():
				self.setVParam(self.getPositional())
		else:
			# TODO defaults?
			if self.positionalArgsRemain():
				# Too many positional parameters
				return self.invalidateTransfer()

		assert cparams.kparam is None

		if returnarglen:
			if len(cparams.returnparams) == returnarglen:
				self.info.numReturns = returnarglen
			else:
				return self.invalidateTransfer()

		return self.info

def computeTransferInfo(code, selfarg, arglen, varglen, returnarglen):
	builder = TransferInfoBuilder()
	info = builder.compute(code, selfarg, arglen, varglen, returnarglen)
	return info
