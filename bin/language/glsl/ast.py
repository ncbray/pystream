from language.base.metaast import *
from glslbase import *

### Type declarations ###
class BuiltinType(Type):
	__fields__    = 'name:str'
	__shared__    = True

class StructureType(Type):
	__fields__    = 'name:str fieldDecl:tuple*'
	__shared__    = True

class ArrayType(Type):
	__fields__    = 'type:Type count:int'
	__shared__    = True


### Data declarations ###
class VariableDecl(ASTNode):
	__fields__    = 'type:Type name:str initializer:(Constant,Constructor)?'
	__shared__    = True

class ConstantDecl(ASTNode):
	__fields__    = 'type:Type name:str initializer:(Constant,Constructor)?'
	__shared__    = True

class UniformDecl(ASTNode):
	__fields__    = 'type:Type name:str initializer:(Constant,Constructor)?'
	__shared__    = True

class InputDecl(ASTNode):
	__fields__    = 'interpolation:str? centroid:bool type:Type name:str'
	__shared__    = True

class OutputDecl(ASTNode):
	__fields__    = 'interpolation:str? centroid:bool invariant:bool type:Type name:str'
	__shared__    = True

#interpolation: (smooth, nonperspective, flat)


### Expressions ###

class Constant(Expression):
	__fields__    = 'type:Type'
	__slots__     = 'object'
	__shared__    = True # HACK because of slots?

	def __init__(self, type, o):
		super(Constant, self).__init__()
		self.type = type
		self.object = o

	def __repr__(self):
		return "%s(%r, %r)" % (type(self).__name__, self.type, self.object)

	def constantValue(self):
		return self.object

class Constructor(Expression):
	__fields__    = 'type:Type args:Expression*'

class BinaryOp(Expression):
	__fields__    = 'left:Expression op:str right:Expression'

class UnaryPrefixOp(Expression):
	__fields__    = 'op:str expr:Expression'

class UnaryPostfixOp(Expression):
	__fields__    = 'expr:Expression op:str'

class IntrinsicOp(Expression):
	__fields__    = 'name:str args:Expression*'

class Load(Expression):
	__fields__    = 'expr:Expression name:str'


class Local(Expression):
	__fields__ = 'type:Type name:str?'
	__shared__ = True

class Uniform(Expression):
	__fields__ = 'decl:UniformDecl'
	__shared__ = True

class Input(Expression):
	__fields__ = 'decl:InputDecl'
	__shared__ = True

class Output(Expression):
	__fields__ = 'decl:OutputDecl'
	__shared__ = True

# HACK lcl can be output?
class Assign(Statement):
	__fields__ = 'expr:Expression lcl:Expression'

class Discard(Statement):
	__fields__ = 'expr:Expression'


class Return(Statement):
	__fields__ = 'expr:Expression?'


class GetAttr(Expression):
	__fields__ = 'expr:Expression name:str'

class SetAttr(Statement):
	__fields__ = 'value:Expression expr:Expression name:str'

class GetSubscript(Expression):
	__fields__ = 'expr:Expression subscript:Expression'

class SetSubscript(Statement):
	__fields__ = 'value:Expression expr:Expression subscript:Expression'

class Suite(ASTNode):
	__fields__ = 'statements:Statement*'

	def __init__(self, statements=None):
		super(Suite, self).__init__()
		self.statements = []
		self.append(statements)

	def insertHead(self, block):
		if block != None:
			if isinstance(block, Suite):
				# Flatten hierachial suites
				self.statements[0:0] = block.statements
			elif isinstance(block, (list, tuple)):
				for child in reversed(block):
					self.insertHead(child)
			else:
				self.statements.insert(0, block)

	def append(self, block):
		if block != None:
			if isinstance(block, Suite):
				# Flatten hierachial suites
				self.statements.extend(block.statements)
			elif isinstance(block, (list, tuple)):
				# Containers
				for child in block:
					self.append(child)
			elif block is not None:
				assert isinstance(block, Statement), block
				self.statements.append(block)

class Parameter(ASTNode):
	__fields__ = 'lcl:Local paramIn:bool paramOut:bool'

class Code(ASTNode):
	__fields__ = 'name:str parameters:Parameter* returnType:Type body:Suite'
