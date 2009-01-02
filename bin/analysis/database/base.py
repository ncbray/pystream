class SchemaError(Exception):
	pass

class DatabaseError(Exception):
	pass

class Schema(object):
	"""
	Schema abstract base class.
	"""

	__slots__ = ()
	
	def __call__(self):
		return self.instance()

	def validateNoRaise(self, args):
		try:
			self.validate(args)
		except SchemaError:
			return False
		else:
			return True
