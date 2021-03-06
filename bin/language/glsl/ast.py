# Copyright 2011 Nicholas Bray
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from glslbase import *

### Type declarations ###
class BuiltinType(Type):
	__fields__    = 'name:str'
	__shared__    = True

	def __repr__(self):
		return "BuiltinType(%s)" % (self.name)

class StructureType(Type):
	__fields__    = 'name:str fieldDecl:VariableDecl*'
	__shared__    = True

class ArrayType(Type):
	__fields__    = 'type:Type count:int'
	__shared__    = True


### Data declarations ###
class VariableDecl(GLSLASTNode):
	__fields__    = 'type:Type name:str initializer:(Constant,Constructor)?'
	__shared__    = True

class ConstantDecl(GLSLASTNode):
	__fields__    = 'type:Type name:str initializer:(Constant,Constructor)?'
	__shared__    = True

class UniformDecl(GLSLASTNode):
	__fields__    = 'builtin:bool type:Type name:str initializer:(Constant,Constructor)?'
	__shared__    = True

	def __repr__(self):
		return "%s(%s)" % (type(self).__name__, self.name)

class InputDecl(GLSLASTNode):
	__fields__    = 'interpolation:str? centroid:bool builtin:bool type:Type name:str'
	__shared__    = True

	def __repr__(self):
		return "%s(%s)" % (type(self).__name__, self.name)


class OutputDecl(GLSLASTNode):
	__fields__    = 'interpolation:str? centroid:bool invariant:bool builtin:bool type:Type name:str'
	__shared__    = True

	def __repr__(self):
		return "%s(%s)" % (type(self).__name__, self.name)

class BlockDecl(GLSLASTNode):
	__fields__ = 'layout:str? name:str decls:UniformDecl*'


class Declarations(GLSLASTNode):
	__fields__ = 'decls*'

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

class Store(Statement):
	__fields__    = 'value:Expression expr:Expression name:str'

class Local(Expression):
	__fields__ = 'type:Type name:str?'
	__shared__ = True

	def __repr__(self):
		if self.name:
			return "Local(%r, %s/%d)" % (self.type, self.name, id(self))
		else:
			return "Local(%r/%d)" % (self.type, id(self))

class Uniform(Expression):
	__fields__ = 'decl:UniformDecl'
	__shared__ = False

class Input(Expression):
	__fields__ = 'decl:InputDecl'
	__shared__ = False

class Output(Expression):
	__fields__ = 'decl:OutputDecl'
	__shared__ = False

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

class ShortCircutAnd(Expression):
	__fields__ = 'exprs:Expression*'

class ShortCircutOr(Expression):
	__fields__ = 'exprs:Expression*'

class Switch(Statement):
	__fields__ = 'condition:Expression t:Suite f:Suite'

class While(Statement):
	__fields__ = 'condition:Expression body:Suite'

class Suite(GLSLASTNode):
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

class Parameter(GLSLASTNode):
	__fields__ = 'lcl:Local paramIn:bool paramOut:bool'

class Code(GLSLASTNode):
	__fields__ = 'name:str params:Parameter* returnType:Type body:Suite'
