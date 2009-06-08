import language.python.ast as ast

class AbstractCode(ast.ASTNode):
	__slots__ = ()

	__shared__ = True

	# HACK types are not unified with ast.Code, so use this to identify
	def isAbstractCode(self):
		return True

	def codeName(self):
		raise NotImplementedError

	def setCodeName(self, name):
		raise NotImplementedError

	def abstractReads(self):
		return None

	def abstractModifies(self):
		return None

	def abstractAllocates(self):
		return None
