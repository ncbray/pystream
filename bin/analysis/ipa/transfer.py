from util import tvl


# TODO pool arg objects?

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
		self.transferOK = tvl.TVLTrue

	def transfer(self, getter, setter):
		if self.selfparam:
			setter.setSelfParam(getter.getSelfArg())

		for i, p in enumerate(self.params):
			setter.setParam(i, p.get(getter))

		for i, p in enumerate(self.vparams):
			setter.setVParam(i, p.get(getter))

		for kwd, p in enumerate(self.kparams):
			setter.setKParam(kwd, p.get(getter))

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

	def dump(self):
		print "="*40
		print self.selfparam
		print self.params
		print self.vparams
		print self.transferOK
		print "="*40
		print


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

	def compute(self, code, selfarg, arglen, varglen):
		self.code    = code

		self.arglen  = arglen
		self.varglen = varglen

		cparams = code.codeParameters()

		if cparams.selfparam is not None:
			if selfarg:
				self.info.selfparam = True
			else:
				# Self arg is missing
				return self.invalidateTransfer()

		for i, param in enumerate(cparams.params):
			if self.positionalArgsRemain():
				self.info.params.append(self.getPositional())
			elif self.defaultExists(i):
				self.info.params.append(self.getDefault(i))
			else:
				# Not enough positional parameters
				return self.invalidateTransfer()

		if cparams.vparam is not None:
			while self.positionalArgsRemain():
				self.info.vparams.append(self.getPositional())
		else:
			# TODO defaults?
			if self.positionalArgsRemain():
				# Too many positional parameters
				return self.invalidateTransfer()

		assert cparams.kparam is None

		return self.info

def computeTransferInfo(code, selfarg, arglen, varglen):
	builder = TransferInfoBuilder()
	info = builder.compute(code, selfarg, arglen, varglen)
	return info
