from util.typedispatch import *
from language.python import ast

class GetOps(TypeDispatcher):
	def __init__(self):
		self.ops    = []
		self.locals = set()

	@dispatch(ast.leafTypes, ast.Break, ast.Continue, ast.Code, ast.DoNotCare)
	def visitLeaf(self, node):
		pass

	@dispatch(ast.Suite, ast.Condition, ast.Assign, ast.Switch, ast.Discard,
		ast.For, ast.While,
		ast.CodeParameters,
		ast.TypeSwitch, ast.TypeSwitchCase, ast.Return)
	def visitOK(self, node):
		node.visitChildren(self)

	@dispatch(ast.Local, ast.Existing)
	def visitLocal(self, node):
		self.locals.add(node)

	@dispatch(ast.Load, ast.Store, ast.Check, ast.Allocate,
		  ast.BinaryOp, ast.Is, ast.UnaryPrefixOp,
		  ast.GetGlobal, ast.SetGlobal,
		  ast.GetSubscript, ast.SetSubscript,
		  ast.Call, ast.DirectCall, ast.MethodCall,
		  ast.UnpackSequence,
		  ast.GetAttr, ast.SetAttr,
		  ast.ConvertToBool, ast.Not,
		  ast.BuildTuple, ast.BuildList, ast.GetIter)
	def visitOp(self, node):
		node.visitChildren(self)
		self.ops.append(node)

	def process(self, node):
		# This is a shared node, so force traversal
		node.visitChildrenForced(self)
		return self.ops, self.locals


def getOps(func):
	go = GetOps()
	go.process(func)
	return go.ops, go.locals
