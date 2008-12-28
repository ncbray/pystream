def isPythonAST(ast):
	return isinstance(ast, ASTNode)

class ASTNode(object):
	__slots__ = '__weakref__'

##	def isConstant(self):
##		return False

	def returnsValue(self):
		return False

	def isPure(self):
		return False

	def isControlFlow(self):
		return False

	def isReference(self):
		return False

class Expression(ASTNode):
	__slots__ = ()
	
	def returnsValue(self):
		return True

class LLExpression(Expression):
	__slots__ = ()
	
	def returnsValue(self):
		return True

class Reference(Expression):
	__slots__ = ()
	
	def isReference(self):
		return True

class Statement(ASTNode):
	__slots__ = ()

class SimpleStatement(Statement):
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
