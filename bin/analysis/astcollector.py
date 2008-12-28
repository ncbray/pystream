from util.typedispatch import *

from programIR.python import ast
from programIR.python import program

class GetOps(object):
	__metaclass__ = typedispatcher

	def __init__(self):
		self.ops    = set()
		self.locals = set()

	@defaultdispatch
	def default(self, node):
		assert False, repr(node)

	@dispatch(str, type(None), ast.Existing, ast.Return)
	def visitJunk(self, node):
		pass

	@dispatch(ast.Suite, ast.Condition, ast.Assign, ast.Switch, ast.Discard, ast.For, ast.While)
	def visitOK(self, node):
		for child in ast.children(node):
			self(child)

	@dispatch(ast.Local)
	def visitLocal(self, node):
		self.locals.add(node)

	@dispatch(ast.Load, ast.Store, ast.Allocate, ast.BinaryOp, ast.UnaryPrefixOp,
		  ast.GetGlobal, ast.SetGlobal,
		  ast.Call, ast.DirectCall, ast.MethodCall,
		  ast.UnpackSequence,
		  ast.GetAttr, ast.SetAttr, ast.ConvertToBool,
		  ast.BuildTuple, ast.BuildList, ast.GetIter)
	def visitOp(self, node):
		self.ops.add(node)

	@dispatch(list)
	def visitList(self, node):
		return [self(child) for child in node]

	@dispatch(tuple)
	def visitTuple(self, node):
		return tuple([self(child) for child in node])

	@dispatch(ast.Code)
	def visitCode(self, node):
		self(node.ast)

	@dispatch(ast.Function)
	def visitFunction(self, node):
		self(node.code)


def getOps(func):
	go = GetOps()
	go(func)
	return go.ops, go.locals
