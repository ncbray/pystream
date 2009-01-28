### Objects for representing decompiled code. ###

# Fields should be in order of evaluation.

from programIR.base.metaast import *
from pythonbase import *

# Allows Existing.object to be typed.
from . import program

class Existing(Reference):
	__metaclass__ = astnode
	__slots__     = 'object'
	__shared__    = True

	def __init__(self, o):
		super(Existing, self).__init__()
		#assert isinstance(o, program.AbstractObject), type(o)
		self.object = o

	def __repr__(self):
		return "%s(%r)" % (type(self).__name__, self.object)

##	def isConstant(self):
##		return True

	def isPure(self):
		return True

	def constantValue(self):
		return self.object.pyobj

	def __eq__(self, other):
		return type(self) is type(other) and self.object is other.object

	def __hash__(self):
		return hash(self.object)


class Local(Reference):
	__metaclass__ = astnode
	__slots__     = 'name'
	__shared__    = True

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
	__metaclass__ = astnode
	__slots__     = 'name'
	__shared__    = True

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
	__metaclass__ = astnode
	__fields__    = 'name'
	__types__     = {'name':Existing}

class SetGlobal(SimpleStatement):
	__metaclass__ = astnode
	__fields__    = 'name', 'value'
	__types__     = {'name':Existing, 'value':Expression}

class DeleteGlobal(SimpleStatement):
	__metaclass__ = astnode
	__fields__    = 'name'
	__types__     = {'name':Existing}


# Gets the actual cell.
class GetCell(Expression):
	__metaclass__ = astnode
	__fields__    = 'cell'
	__types__     = {'cell':Cell}

	def isPure(self):
		return True


# Gets the contents of a cell.
class GetCellDeref(Expression):
	__metaclass__ = astnode
	__fields__    = 'cell'
	__types__     = {'cell':Cell}

# Sets the contents of a cell.
class SetCellDeref(SimpleStatement):
	__metaclass__ = astnode
	__fields__    = 'value', 'cell'
	__types__     = {'cell':Cell, 'value':Expression}


class Yield(Expression):
	__metaclass__ 	= astnode
	__fields__ 	= 'expr'
	__types__ 	= {'expr':Expression}

class GetIter(Expression):
	__metaclass__ 	= astnode
	__fields__ 	= 'expr'
	__types__ 	= {'expr':Expression}

class ConvertToBool(Expression):
	__metaclass__ 	= astnode
	__fields__ 	= 'expr'
	__types__ 	= {'expr':Expression}

class Import(Expression):
	__metaclass__ 	= astnode
	__fields__ 	= 'name', 'fromlist', 'level'
	__types__ 	= {'name':str, 'fromlist':(tuple, list), 'level':int}
	__optional__ 	= 'fromlist'

# TODO make UnaryPrefixOp? It is in a class of its own...
class Not(Expression):
	__metaclass__ 	= astnode
	__fields__ 	= 'expr'
	__types__ 	= {'expr':Expression}

class UnaryPrefixOp(Expression):
	__metaclass__ 	= astnode
	__fields__ 	= 'op', 'expr'
	__types__ 	= {'op':str, 'expr':Expression}

class BinaryOp(Expression):
	__metaclass__ 	= astnode
	__fields__ 	= 'left', 'op', 'right'
	__types__ 	= {'left':Expression, 'op':str, 'right':Expression}

class GetSubscript(Expression):
	__metaclass__ = astnode
	__fields__    = 'expr', 'subscript'
	__types__     = {'expr':Expression, 'subscript':Expression}

class SetSubscript(SimpleStatement):
	__metaclass__ = astnode
	__fields__    = 'value', 'expr', 'subscript'
	__types__     = {'value':Expression, 'expr':Expression, 'subscript':Expression}

class DeleteSubscript(SimpleStatement):
	__metaclass__ = astnode
	__fields__    = 'expr', 'subscript'
	__types__     = {'expr':Expression, 'subscript':Expression}


class GetSlice(Expression):
	__metaclass__ = astnode
	__fields__    = 'expr', 'start', 'stop', 'step'
	__types__     = {'expr':Expression, 'start':Expression, 'step':Expression, 'step':Expression}
	__optional__  = 'start', 'stop', 'step'


class SetSlice(SimpleStatement):
	__metaclass__ = astnode
	__fields__    = 'value', 'expr', 'start', 'stop', 'step',
	__types__     = {'value':Expression, 'expr':Expression, 'start':Expression, 'step':Expression, 'step':Expression}
	__optional__  = 'start', 'stop', 'step'

class DeleteSlice(SimpleStatement):
	__metaclass__ 	= astnode
	__fields__ 	= 'expr', 'start', 'stop', 'step'
	__types__ 	= {'expr':Expression, 'start':Expression, 'step':Expression, 'step':Expression}
	__optional__ 	= 'start', 'stop', 'step'


class Call(Expression):
	__metaclass__ 	= astnode
	__fields__ 	= 'expr', 'args', 'kwds', 'vargs', 'kargs'
	__types__ 	= {'expr':Expression, 'args':(list, tuple), 'kwds':(list, tuple)}
	__optional__ 	= 'vargs', 'kargs'


class MethodCall(Expression):
	__metaclass__ 	= astnode
	__fields__ 	= 'expr', 'name', 'args', 'kwds', 'vargs', 'kargs'
	__types__ 	= {'expr':Expression, 'name':Expression, 'args':(list, tuple), 'kwds':(list, tuple)}
	__optional__ 	= 'vargs', 'kargs'


class DirectCall(Expression):
	__metaclass__ 	= astnode
	__fields__ 	= 'func', 'selfarg', 'args', 'kwds', 'vargs', 'kargs'
	__types__ 	= {'selfarg':Expression, 'args':(list, tuple), 'kwds':(list, tuple),
			   'vargs':Expression, 'kargs':Expression,
			   'func':'Code'}
	__optional__ 	= 'selfarg', 'vargs', 'kargs'

	def __repr__(self):
		return "%s(<%s>, %r, %r, %r, %r, %r)" % (type(self).__name__, self.func.name,
						       self.selfarg,
						       self.args, self.kwds,
						       self.vargs, self.kargs)

class BuildTuple(Expression):
	__metaclass__ 	= astnode
	__fields__ 	= 'args'
	__types__ 	= {'args':(tuple, list)}

	def isPure(self):
		return True

class BuildList(Expression):
	__metaclass__ = astnode
	__fields__    = 'args'
	__types__     = {'args':(tuple, list)}

	def isPure(self):
		return True

class BuildMap(Expression):
	__metaclass__ = astnode

	def isPure(self):
		return True

class BuildSlice(Expression):
	__metaclass__ = astnode
	__fields__    = 'start', 'stop', 'step'
	__types__     = {'start':Expression, 'step':Expression, 'step':Expression}
	__optional__  = 'start', 'stop', 'step'

	def isPure(self):
		return True

class GetAttr(Expression):
	__metaclass__ = astnode
	__fields__    = 'expr', 'name'
	__types__     = {'expr':Expression, 'name':Expression}

class SetAttr(SimpleStatement):
	__metaclass__ = astnode
	__fields__    = 'value', 'expr', 'name'
	__types__     = {'value':Expression, 'expr':Expression, 'name':Expression}

class DeleteAttr(SimpleStatement):
	__metaclass__ = astnode
	__fields__    = 'expr', 'name'
	__types__     = {'expr':Expression, 'name':Expression}

class UnpackSequence(SimpleStatement):
	__metaclass__ = astnode
	__fields__    = 'expr', 'targets'
	__types__     = {'targets':(tuple, list), 'expr':Expression}

# TODO should swap expr/lcl?
class Assign(SimpleStatement):
	__metaclass__ = astnode
	__fields__    = 'expr', 'lcl'
	__slots__     = 'isSplit', 'isMerge'
	__types__     = {'expr':Expression, 'lcl':Local}

	def __init__(self, expr, lcl):
		super(Assign, self).__init__()
		assert expr.returnsValue(), expr
		assert isinstance(lcl, Local), lcl

		self.expr = expr
		self.lcl = lcl

		self.isSplit = False
		self.isMerge = False

	def markSplit(self):
		self.isSplit = True

	def markMerge(self):
		self.isMerge = True

class Discard(SimpleStatement):
	__metaclass__ = astnode
	__fields__    = 'expr'
	__types__     = {'expr':Expression}

class Delete(SimpleStatement):
	__metaclass__ = astnode
	__fields__    = 'lcl'
	__types__     = {'lcl':Local}


class Print(SimpleStatement):
	__metaclass__ = astnode
	__fields__    = 'target', 'expr'
	__types__     = {'target':Expression, 'expr':Expression}
	__optional__  = 'target', 'expr'

class MakeFunction(Expression):
	__metaclass__ = astnode
	__fields__    = 'defaults', 'cells', 'code'
	__types__     = {'defaults':(tuple, list), 'cells':(tuple, list)}

	def isPure(self):
		return True

### Short circut evaluation ###
class ShortCircutAnd(Expression):
	__metaclass__ = astnode
	__fields__    = 'terms'
	__types__     = {'terms':(list, tuple)}

class ShortCircutOr(Expression):
	__metaclass__ = astnode
	__fields__    = 'terms'
	__types__     = {'terms':(list, tuple)}

### Control flow ###
class Return(ControlFlow):
	__metaclass__ = astnode
	__fields__    = 'expr'
	__types__     = {'expr':Expression}
#	__optional__  = 'expr'


# Order of evaluation verified emperically.
# Documentation contradicts.
class Raise(ControlFlow):
	__metaclass__ = astnode
	__fields__    = 'exception', 'parameter', 'traceback'
	__optional__  = 'exception', 'parameter', 'traceback'


class Continue(ControlFlow):
	__metaclass__ 	= astnode

class Break(ControlFlow):
	__metaclass__ 	= astnode

# A temorary AST node used while decompiling.
class EndFinally(ControlFlow):
	__metaclass__ 	= astnode





###########
### CFG ###
###########

def flattenSuite(blocks, out):
	if isinstance(blocks, (list, tuple)):
		for block in blocks:
			flattenSuite(block, out)
	elif blocks is not None:
		out.append(blocks)

class Suite(ASTNode):
	__metaclass__ 	= astnode
	__fields__ 	= 'blocks'
	__types__ 	= {'blocks':list}

	def __init__(self, blocks=None):
		super(Suite, self).__init__()
		self.blocks = []
		flattenSuite(blocks, self.blocks)

	def insertHead(self, block):
		if block != None:
			if isinstance(block, Suite):
				# Flatten hierachial suites
				self.blocks[0:0] = block.blocks
			else:
				self.blocks.insert(0, block)

	def append(self, block):
		if block != None:
			if isinstance(block, Suite):
				# Flatten hierachial suites
				self.blocks.extend(block.blocks)
			else:
				self.blocks.append(block)

	def significant(self):
		#return bool(self.onEntry or self.onExit or self.blocks)
		return bool(self.blocks)


class ExceptionHandler(ASTNode):
	__metaclass__ 	= astnode
	__fields__ 	= 'preamble', 'type', 'value', 'body'
	__type__ 	= {'preamble':Suite, 'type':Expression, 'value':Expression, 'body':Suite}
	__optional__ 	= 'value'


class Condition(CompoundStatement):
	__metaclass__ 	= astnode
	__fields__ = 'preamble', 'conditional'
	__types__ = {'preamble':Suite, 'conditional':Expression}


class Switch(CompoundStatement):
	__metaclass__ 	= astnode
	__fields__ 	= 'condition', 't', 'f',
	__types__ 	= {'condition':Condition, 't':Suite,'f':Suite}

class TryExceptFinally(CompoundStatement):
	__metaclass__ 	= astnode
	__fields__ 	= 'body', 'handlers', 'defaultHandler', 'else_', 'finally_'
	__types__ 	= {'body':Suite, 'handlers':(list, tuple),
			   'else_':Suite, 'finally_':Suite}
	__optional__ = 'defaultHandler', 'else_', 'finally_'

class Loop(CompoundStatement):
	__slots__ = ()

class While(Loop):
	__metaclass__ 	= astnode
	__fields__ 	= 'condition', 'body', 'else_'
	__types__ 	= {'condition':Condition, 'body':Suite, 'else_':Suite}
	#__optional__ 	= 'else_'


class For(Loop):
	__metaclass__ 	= astnode
	__fields__ 	= 'iterator', 'index', 'loopPreamble', 'bodyPreamble', 'body', 'else_'
	__types__ 	= {'iterator':Expression, 'body':Suite, 'else_':Suite, 'bodyPreamble':Suite,}
	# TODO type of index?

#argnames -> list(str)
#parameters -> list(Local)
class Code(CompoundStatement):
	__metaclass__ 	= astnode

	__fields__ 	= ('name', 'selfparam', 'parameters', 'parameternames',
			   'vparam', 'kparam', 'returnparam', 'ast',)

	__types__ 	= {'name':str,
			   'selfparam':Local,
			   'parameternames':(tuple, list),
			   'parameters':(tuple, list),
			   'vparam':Local, 'kparam':Local,
			   'returnparam':Local,
			   'ast':Suite}

	#__optional__ 	= 'selfparam', 'vparam', 'kparam'
	# HACK for function cloning.
	__optional__ 	= 'selfparam', 'parameters', 'parameternames', 'vparam', 'kparam', 'returnparam', 'ast'
	__shared__      = True

	def __repr__(self):
		return "Code(%s/%d)" % (self.name, id(self))

# TODO what's the type?
class Function(CompoundStatement):
	__metaclass__ 	= astnode
	__fields__ 	= 'name', 'code'
	__types__ 	= {'name':str, 'code':Code}
	__optional__    = 'code' # HACK for function cloning, allows function to be created without code.
	__shared__      = True



class Allocate(LLExpression):
	__metaclass__ = astnode
	__fields__    = 'expr'
	__types__     = {'expr':Reference}

class Load(LLExpression):
	__metaclass__ = astnode
	__fields__    = 'expr', 'fieldtype', 'name'
	__types__     = {'expr':Reference, 'fieldtype':str, 'name':Reference}

class Store(LLStatement):
	__metaclass__ = astnode
	__fields__    = 'expr', 'fieldtype', 'name', 'value'
	__types__     = {'expr':Reference, 'fieldtype':str, 'name':Reference, 'value':Reference}

manifest = makeASTManifest(globals())




