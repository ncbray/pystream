from util.typedispatch import *
import util.traversal

from language.python import ast
from language.python import program

from common import opnames


class ConvertCalls(TypeDispatcher):
	def __init__(self, extractor, code):
		self.extractor = extractor
		self.code = code

	def directCall(self, node, code, selfarg, args, vargs=None, kargs=None):
		kwds = [] # HACK
		result = ast.DirectCall(code, selfarg, args, kwds, vargs, kargs)
		if node is not None:
			result.annotation = node.annotation
		return result

	@property
	def exports(self):
		return self.extractor.stubs.exports

	@defaultdispatch
	def default(self, node):
		assert False, repr(type(node))

	@dispatch(str, type(None), ast.Local, ast.Existing, ast.Code, ast.Break, ast.Continue, ast.CodeParameters)
	def visitLeaf(self, node):
		return node

	@dispatch(ast.Suite, ast.Condition, list, tuple,
		  ast.Assign, ast.Discard, ast.Return,
		  ast.Allocate, ast.Store, ast.Load, ast.Check,
		  ast.Switch, ast.For, ast.While,
		  ast.TypeSwitch, ast.TypeSwitchCase)
	def visitOK(self, node):
		return allChildren(self, node)

	@dispatch(ast.Call, ast.DirectCall, ast.MethodCall)
	def visitCall(self, node):
		return allChildren(self, node)

	@dispatch(ast.ConvertToBool)
	def visitConvertToBool(self, node):
		return self.directCall(node, self.exports['convertToBool'], None, [self(node.expr)])

	@dispatch(ast.Not)
	def visitNot(self, node):
		return self.directCall(node, self.exports['invertedConvertToBool'], None, [self(node.expr)])


	@dispatch(ast.BinaryOp)
	def visitBinaryOp(self, node):
		if node.op in opnames.inplaceOps:
			opname = opnames.inplace[node.op[:-1]]
		else:
			opname = opnames.forward[node.op]

		return self.directCall(node, self.exports['interpreter%s' % opname], None, [self(node.left), self(node.right)])

	@dispatch(ast.UnaryPrefixOp)
	def visitUnaryPrefixOp(self, node):
		opname = opnames.unaryPrefixLUT[node.op]
		return self.directCall(node, self.exports['interpreter%s' % opname], None, [self(node.expr)])

	@dispatch(ast.GetGlobal)
	def visitGetGlobal(self, node):
		p = self.code.codeparameters
		return self.directCall(node, self.exports['interpreterLoadGlobal'], None, [self(p.selfparam), self(node.name)])

	@dispatch(ast.SetGlobal)
	def visitSetGlobal(self, node):
		p = self.code.codeparameters
		call = self.directCall(node, self.exports['interpreterStoreGlobal'], None, [self(p.selfparam), self(node.name), self(node.value)])
		return ast.Discard(call)


	@dispatch(ast.GetIter)
	def visitGetIter(self, node):
		return self.directCall(node, self.exports['interpreter_iter'], None, [self(node.expr)])


	@dispatch(ast.BuildList)
	def visitBuildList(self, node):
		return self.directCall(node, self.exports['buildList'], None, self(node.args))

	@dispatch(ast.BuildTuple)
	def visitBuildTuple(self, node):
		#code = self.exports['buildTuple']
		code = self.exports['interpreter_buildTuple%d' % len(node.args)]
		return self.directCall(node, code, None, self(node.args))

	@dispatch(ast.UnpackSequence)
	def visitUnpackSequence(self, node):
		# HACK oh so ugly... does not resemble what actually happens.
		if True:
			dc = self.directCall(node, self.exports['interpreter_unpack%d' % len(node.targets)], None, [self(node.expr)])
			return ast.Assign(dc, node.targets)
		else:
			calls = []

			for i, arg in enumerate(node.targets):
				obj = self.extractor.getObject(i)
				call = self.directCall(None, self.exports['interpreter_getitem'], None, [self(node.expr), self(ast.Existing(obj))])
				calls.append(ast.Assign(call, [arg]))

			return calls

	@dispatch(ast.GetAttr)
	def visitGetAttr(self, node):
		return self.directCall(node, self.exports['interpreter_getattribute'], None, [self(node.expr), self(node.name)])

	@dispatch(ast.SetAttr)
	def visitSetAttr(self, node):
		return ast.Discard(self.directCall(node, self.exports['interpreter_setattr'], None, [self(node.expr), self(node.name), self(node.value)]))

	@dispatch(ast.GetSubscript)
	def visitGetSubscript(self, node):
		return self.directCall(node, self.exports['interpreter_getitem'], None, [self(node.expr), self(node.subscript)])

	@dispatch(ast.SetSubscript)
	def visitSetSubscript(self, node):
		return ast.Discard(self.directCall(node, self.exports['interpreter_setitem'], None, [self(node.expr), self(node.subscript), self(node.value)]))


def callConverter(extractor, node):
	converter = ConvertCalls(extractor, node)
	util.traversal.replaceAllChildren(converter, node)
	return node
