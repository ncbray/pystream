class Constraint(object):
	__slots__ = ()

	def init(self, context):
		self.attach()
		self.makeConsistent(context)
