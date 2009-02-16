from .. import annotations


emptyCodeAnnotation  = annotations.CodeAnnotation()
emptyOpAnnotation    = annotations.OpAnnotation()
emptySlotAnnotation  = annotations.SlotAnnotation()

def isPythonAST(ast):
	return isinstance(ast, ASTNode)

class ASTNode(object):
	__slots__ = 'annotation'

	emptyAnnotation = None

	def __init__(self):
		self.annotation = self.emptyAnnotation

	def returnsValue(self):
		return False

	def isPure(self):
		return False

	def isControlFlow(self):
		return False

	def isReference(self):
		return False

	def rewriteAnnotation(self, **kwds):
		self.annotation = self.annotation.rewrite(**kwds)

class Expression(ASTNode):
	__slots__ = ()

	emptyAnnotation = emptyOpAnnotation

	def returnsValue(self):
		return True

class LLExpression(Expression):
	__slots__ = ()

	def returnsValue(self):
		return True

class Reference(Expression):
	__slots__ = ()

	emptyAnnotation = emptySlotAnnotation

	def isReference(self):
		return True

class Statement(ASTNode):
	__slots__ = ()

	emptyAnnotation = emptyOpAnnotation

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
