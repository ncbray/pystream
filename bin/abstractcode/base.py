class AbstractCode(object):
	__slots__ = ()

	# HACK types are not unified with ast.Code, so use this to identify
	def isAbstractCode(self):
		return True

	def codeName(self):
		raise NotImplementedError