from asttools.metaast import ASTNode
from . import annotations

def isPythonAST(ast):
	return isinstance(ast, PythonASTNode)

class PythonASTNode(ASTNode):
	def __init__(self):
		raise NotImplementedError
	
	def returnsValue(self):
		return False

	def alwaysReturnsBoolean(self):
		return False

	def isPure(self):
		return False

	def isControlFlow(self):
		return False

	def isReference(self):
		return False

	def isCode(self):
		return False

class Expression(PythonASTNode):
	__slots__ = ()

	__emptyAnnotation__ = annotations.emptyOpAnnotation

	def returnsValue(self):
		return True

class LLExpression(Expression):
	__slots__ = ()

	def returnsValue(self):
		return True

class Reference(Expression):
	__slots__ = ()

	__emptyAnnotation__ = annotations.emptySlotAnnotation

	def isReference(self):
		return True

	def isDoNotCare(self):
		return False

class Statement(PythonASTNode):
	__slots__ = ()

	__emptyAnnotation__ = annotations.emptyOpAnnotation

class SimpleStatement(Statement):
	__slots__ = ()

class LLStatement(SimpleStatement):
	__slots__ = ()

class ControlFlow(SimpleStatement):
	__slots__ = ()

	def significant(self):
		return True

	def isControlFlow(self):
		return True

class CompoundStatement(Statement):
	__slots__ = ()

	def significant(self):
		return True


class BaseCode(PythonASTNode):
	__slots__ = ()
	__shared__ = True

	def isCode(self):
		return True

	def isAbstractCode(self):
		return False

	def isStandardCode(self):
		return False

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


class AbstractCode(BaseCode):
	__slots__ = ()
	__shared__ = True

	def isAbstractCode(self):
		return True