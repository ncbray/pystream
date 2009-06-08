### Objects for representing decompiled code. ###

# Fields should be in order of evaluation.

from language.base.metaast import *
from pythonbase import *

# Allows Existing.object to be typed.
from . import program

# For Code
import util.calling

# HACK for CodeParameters.paramnames
NoneType = type(None)

class Existing(Reference):
	__slots__  = 'object'
	__shared__ = True

	def __init__(self, o):
		super(Existing, self).__init__()
		assert isinstance(o, program.AbstractObject), type(o)
		self.object = o

	def __repr__(self):
		return "%s(%r)" % (type(self).__name__, self.object)

##	def isConstant(self):
##		return True

	def isPure(self):
		return True

	def constantValue(self):
		return self.object.pyobj

class Local(Reference):
	__slots__  = 'name'
	__shared__ = True

	def __init__(self, name=None):
		super(Local, self).__init__()
		self.name = name

	def __repr__(self):
		if self.name:
			return "Local(%s/%d)" % (self.name, id(self))
		else:
			return "Local(%d)" % id(self)

	def __hash__(self):
		return id(self)

	def isPure(self):
		return True


class Cell(ASTNode):
	__slots__  = 'name'
	__shared__ = True

	def __init__(self, name):
		super(Cell, self).__init__()
		assert isinstance(name, str)
		self.name = name

	def __eq__(self, other):
		if isinstance(other, type(self)):
			return self.name == other.name
		else:
			return False

	def __hash__(self):
		return hash(self.name)

	def isPure(self):
		return True

	def __repr__(self):
		return "%s(%r)" % (type(self).__name__, self.name)



class GetGlobal(Expression):
	__fields__ = 'name:Existing'

class SetGlobal(SimpleStatement):
	__fields__ = 'name:Existing value:Expression'

class DeleteGlobal(SimpleStatement):
	__fields__ = 'name:Existing'


# Gets the actual cell.
class GetCell(Expression):
	__fields__ = 'cell:Cell'

	def isPure(self):
		return True


# Gets the contents of a cell.
class GetCellDeref(Expression):
	__fields__ = 'cell:Cell'

# Sets the contents of a cell.
class SetCellDeref(SimpleStatement):
	__fields__    = 'value:Expression cell:Cell'


class Yield(Expression):
	__fields__ = 'expr:Expression'

class GetIter(Expression):
	__fields__ = 'expr:Expression'

class ConvertToBool(Expression):
	__fields__ = 'expr:Expression'

class Import(Expression):
	# TODO fromlist type?
	__fields__ = 'name:str fromlist*? level:int'

# TODO make UnaryPrefixOp? It is in a class of its own...
class Not(Expression):
	__fields__ = 'expr:Expression'

class UnaryPrefixOp(Expression):
	__fields__ = 'op:str expr:Expression'

class BinaryOp(Expression):
	__fields__ = 'left:Expression op:str right:Expression'

class GetSubscript(Expression):
	__fields__ = 'expr:Expression subscript:Expression'

class SetSubscript(SimpleStatement):
	__fields__ = 'value:Expression expr:Expression subscript:Expression'

class DeleteSubscript(SimpleStatement):
	__fields__ = 'expr:Expression subscript:Expression'


class GetSlice(Expression):
	__fields__ = 'expr:Expression start:Expression? stop:Expression? step:Expression?'

class SetSlice(SimpleStatement):
	__fields__ = 'value:Expression expr:Expression start:Expression? stop:Expression? step:Expression?'

class DeleteSlice(SimpleStatement):
	__fields__ = 'expr:Expression start:Expression? stop:Expression? step:Expression?'


class Call(Expression):
	__fields__ = 'expr:Expression args:Expression* kwds* vargs:Expression? kargs:Expression?'

class MethodCall(Expression):
	# TODO kwds type?
	__fields__ = 'expr:Expression name:Expression args:Expression* kwds* vargs:Expression? kargs:Expression?'

class DirectCall(Expression):
	# TODO kwds type?
	# HACK code is optional, as cloned "dead" direct calls may have no corresponding code.
	__fields__ = 'code:Code? selfarg:Expression? args:Expression* kwds* vargs:Expression? kargs:Expression?'

	def __repr__(self):
		if self.code is not None:
			codename = self.code.codeName()
		else:
			codename = "???"

		return "%s(<%s>, %r, %r, %r, %r, %r)" % (type(self).__name__, codename,
						       self.selfarg,
						       self.args, self.kwds,
						       self.vargs, self.kargs)

# The args may be all Cells if we're making a closure.
class BuildTuple(Expression):
	__fields__ = 'args:(Expression,Cell)*'

	def isPure(self):
		return True

class BuildList(Expression):
	__fields__ = 'args:Expression*'

	def isPure(self):
		return True

class BuildMap(Expression):

	def isPure(self):
		return True

class BuildSlice(Expression):
	__fields__ = 'start:Expression? stop:Expression? step:Expression?'

	def isPure(self):
		return True

class GetAttr(Expression):
	__fields__ = 'expr:Expression name:Expression'

class SetAttr(SimpleStatement):
	__fields__ = 'value:Expression expr:Expression name:Expression'

class DeleteAttr(SimpleStatement):
	__fields__ = 'expr:Expression name:Expression'

class UnpackSequence(SimpleStatement):
	__fields__ = 'expr:Expression targets:Local*'

# TODO remove markSplit/markMerge?
class Assign(SimpleStatement):
	__fields__ = 'expr:Expression lcls:Local*'

	def markSplit(self):
		pass #self.isSplit = True

	def markMerge(self):
		pass #self.isMerge = True

class Discard(SimpleStatement):
	__fields__ = 'expr:Expression'

class Delete(SimpleStatement):
	__fields__ = 'lcl:Local'

class Print(SimpleStatement):
	__fields__ = 'target:Expression? expr:Expression?'

class MakeFunction(Expression):
	# TODO type?
	__fields__ = 'defaults* cells* code'

	def isPure(self):
		return True

### Short circut evaluation ###
class ShortCircutAnd(Expression):
	# TODO type?
	__fields__ = 'terms*'

class ShortCircutOr(Expression):
	# TODO type?
	__fields__ = 'terms*'

### Control flow ###
class Return(ControlFlow):
	__fields__ = 'exprs:Expression*'

# Order of evaluation verified emperically.
# Documentation contradicts.
class Raise(ControlFlow):
	# TODO types?
	__fields__ = 'exception? parameter? traceback?'

class Continue(ControlFlow):
	pass

class Break(ControlFlow):
	pass

# A temorary AST node used while decompiling.
class EndFinally(ControlFlow):
	pass


###########
### CFG ###
###########

class Suite(ASTNode):
	__fields__ = 'blocks:Statement*'
	__mutable__ = True # HACK not really mutable, just need to be able to assign to blocks.

	def __init__(self, blocks=None):
		super(Suite, self).__init__()
		self.blocks = []
		self.append(blocks)

	def insertHead(self, block):
		if block != None:
			if isinstance(block, Suite):
				# Flatten hierachial suites
				self.blocks[0:0] = block.blocks
			elif isinstance(block, (list, tuple)):
				for child in reversed(block):
					self.insertHead(child)
			else:
				self.blocks.insert(0, block)

	def append(self, block):
		if block != None:
			if isinstance(block, Suite):
				# Flatten hierachial suites
				self.blocks.extend(block.blocks)
			elif isinstance(block, (list, tuple)):
				# Containers
				for child in block:
					self.append(child)
			elif block is not None:
				assert isinstance(block, Statement), block
				self.blocks.append(block)

	def significant(self):
		#return bool(self.onEntry or self.onExit or self.blocks)
		return bool(self.blocks)


class ExceptionHandler(ASTNode):
	__fields__ = 'preamble:Suite type:Expression value:Expression? body:Suite'

class Condition(CompoundStatement):
	__fields__ = 'preamble:Suite conditional:Expression'

class Switch(CompoundStatement):
	__fields__ = 'condition:Condition t:Suite f:Suite'

class TryExceptFinally(CompoundStatement):
	__fields__ = 'body:Suite', 'handlers:ExceptionHandler*', 'defaultHandler?', 'else_:Suite?', 'finally_:Suite?'

class Loop(CompoundStatement):
	__slots__ = ()

class While(Loop):
	__fields__ = 'condition:Condition body:Suite else_:Suite'

class For(Loop):
	__fields__ = 'iterator:Expression index:Local loopPreamble:Suite bodyPreamble:Suite body:Suite else_:Suite'
	# TODO type of index?

class CodeParameters(ASTNode):
	# TODO support paramnames:str?* (different than paramnames:str*?)
	__fields__ = """selfparam:Local?
			params:Local* paramnames:(str,NoneType)*
			vparam:Local? kparam:Local?
			returnparams:Local*"""

	def codeParameters(self):
		return util.calling.CalleeParams(self.selfparam, self.params, self.paramnames, [], self.vparam, self.kparam, self.returnparams)


class Code(CompoundStatement):
	__fields__ = """name:str
			codeparameters:CodeParameters
			ast:Suite"""
	__shared__      = True

	__emptyAnnotation__ = annotations.emptyCodeAnnotation

	def __repr__(self):
		return "Code(%s/%d)" % (self.name, id(self))

	### The abstract code interface ###
	def isAbstractCode(self):
		return True

	def isStandardCode(self):
		return True

	def codeName(self):
		return self.name

	def setCodeName(self, name):
		self.name = name

	def codeParameters(self):
		return self.codeparameters.codeParameters()

	def abstractReads(self):
		return None

	def abstractModifies(self):
		return None

	def abstractAllocates(self):
		return None


class Allocate(LLExpression):
	__fields__ = 'expr:Reference'

class Load(LLExpression):
	__fields__ = 'expr:Reference fieldtype:str name:Reference'

class Store(LLStatement):
	__fields__ = 'expr:Reference fieldtype:str name:Reference value:Reference'

class Check(LLExpression):
	__fields__ = 'expr:Reference fieldtype:str name:Reference'

manifest = makeASTManifest(globals())




