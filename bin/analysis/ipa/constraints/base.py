class Constraint(object):
	__slots__ = ()

	def init(self, context):
		self.attach()
		self.makeConsistent(context)

	def isCopy(self):
		return False

	def isLoad(self):
		return False

	def isStore(self):
		return False

	def isSplit(self):
		return False
