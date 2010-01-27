class CallBinder(object):
	def __init__(self, call, context):
		# Source
		self.call    = call
		self.invoke  = call.context.getInvoke(call.op, context)

		# Desination
		self.context = context
		self.params  = self.context.signature.code.codeParameters()


	def getSelfArg(self):
		return self.call.selfarg

	def getArg(self, i):
		return self.call.args[i]

	def getVArg(self, i):
		return self.call.varg[i]


	def unusedSelfParam(self):
		pass

	def unusedParam(self, i):
		pass

	def unusedVParam(self, i):
		pass


	def setSelfParam(self, value):
		typeFilter = self.context.signature.selfparam
		dst = self.context.local(self.params.selfparam)
		self.copyDownFiltered(value, typeFilter, dst)

	def setParam(self, i, value):
		typeFilter = self.context.signature.params[i]
		dst = self.context.local(self.params.params[i])
		self.copyDownFiltered(value, typeFilter, dst)

	def setVParam(self, i, value):
		typeFilter = self.context.signature.vparams[i]
		dst = self.context.vparamField[i]
		self.copyDownFiltered(value, typeFilter, dst)

	def getReturnParam(self, i):
		return self.context.returns[i]

	def setReturnArg(self, i, value):
		target = self.call.targets[i]
		self.invoke.up(value, target)

	def copyDownFiltered(self, src, typeFilter, dst):
		self.invoke.down(src.getFiltered(typeFilter), dst)

def bind(call, context, info):
	binder = CallBinder(call, context)
	info.transfer(binder, binder)
