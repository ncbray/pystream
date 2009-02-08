from util.typedispatch import *

from programIR.python import ast
from programIR.python import program

from common import opnames


##oldDispatch = dispatch
##
##def dispatch(*types):
##	def traceF(f):
##		def traceWrap(*args, **kargs):
##			print "TRACE", [type(arg) for arg in args[1:]]
##			return f(*args, **kargs)
##		return oldDispatch(*types)(traceWrap)
##	return traceF

class ConvertCalls(object):
	__metaclass__ = typedispatcher

	def __init__(self, extractor, adb, code):
		self.extractor = extractor
		self.adb = adb
		self.code = code

	def directCall(self, node, code, selfarg, args, vargs=None, kargs=None):
		kwds = [] # HACK
		result = ast.DirectCall(code, selfarg, args, kwds, vargs, kargs)
		self.adb.trackRewrite(self.code, node, result)
		return result

	@property
	def exports(self):
		return self.extractor.stubs.exports

	@defaultdispatch
	def default(self, node):
		assert False, repr(type(node))

	@dispatch(str, type(None), ast.Local, ast.Existing, ast.Code, ast.Break, ast.Continue)
	def visitLeaf(self, node):
		return node

	@dispatch(ast.Suite, ast.Condition, list, tuple,
		  ast.Assign, ast.Discard, ast.Return,
		  ast.Allocate, ast.Store, ast.Load, ast.Check,
		  ast.Switch, ast.For, ast.While)
	def visitOK(self, node):
		nodeT = allChildren(self, node)
		self.adb.trackRewrite(self.code, node, nodeT)
		return nodeT

	@dispatch(ast.Call, ast.DirectCall, ast.MethodCall)
	def visitCall(self, node):
		nodeT = allChildren(self, node)
		self.adb.trackRewrite(self.code, node, nodeT)
		return nodeT

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
		return self.directCall(node, self.exports['interpreterLoadGlobal'], None, [self(self.code.selfparam), self(node.name)])

	@dispatch(ast.SetGlobal)
	def visitSetGlobal(self, node):
		call = self.directCall(node, self.exports['interpreterStoreGlobal'], None, [self(self.code.selfparam), self(node.name), self(node.value)])
		return ast.Discard(call)


	@dispatch(ast.GetIter)
	def visitGetIter(self, node):
		return self.directCall(node, self.exports['interpreter_iter'], None, [self(node.expr)])


	@dispatch(ast.BuildList)
	def visitBuildList(self, node):
		return self.directCall(node, self.exports['buildList'], None, self(node.args))

	@dispatch(ast.BuildTuple)
	def visitBuildTuple(self, node):
		return self.directCall(node, self.exports['buildTuple'], None, self(node.args))

	@dispatch(ast.UnpackSequence)
	def visitUnpackSequence(self, node):
		# HACK oh so ugly... does not resemble what actually happens.
		# HACK does not track rewriting, as it is single -> multi
		calls = []

		for i, arg in enumerate(node.targets):
			obj = self.extractor.getObject(i)
			call = self.directCall(arg, self.exports['interpreter_getitem'], None, [self(node.expr), self(ast.Existing(obj))])
			calls.append(ast.Assign(call, arg))

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


##	def visitWhile(self, node):
##		self.visit(node.condition)
##		self.visit(node.body)
##		if node.else_: self.visit(node.else_)
##
##	@dispatch(ast.For)
##	def visitFor(self, node):
##		iterator = self(node.iterator)
##
##		self.directCall(node.index, self.exports['interpreter_next'], None, [iterator])
##
##		self(node.body)
##
##		if node.else_:
##			self(node.else_)


def callConverter(extractor, adb, node):
	assert isinstance(node, ast.Code), node
	node.ast = ConvertCalls(extractor, adb, node)(node.ast)
	return node
