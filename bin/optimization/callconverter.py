from util.typedispatch import *

from programIR.python import ast
from programIR.python import program

from common import opnames
from stubs.stubcollector import exports


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


	@defaultdispatch
	def default(self, node):
		assert False, repr(type(node))

	@dispatch(str, type(None), ast.Local, ast.Existing, ast.Code)
	def visitLeaf(self, node):
		return node

	@dispatch(ast.Suite, ast.Condition, list, tuple,
		  ast.Assign, ast.Discard, ast.Return, ast.Allocate, ast.Store, ast.Load, ast.Switch,
		  ast.For, ast.While)
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
		return self.directCall(node, exports['convertToBool'].code, None, [self(node.expr)])


	@dispatch(ast.BinaryOp)
	def visitBinaryOp(self, node):
		if node.op in opnames.inplaceOps:
			opname = opnames.inplace[node.op[:-1]]
		else:
			opname = opnames.forward[node.op]

		return self.directCall(node, exports['interpreter%s' % opname].code, None, [self(node.left), self(node.right)])

	@dispatch(ast.UnaryPrefixOp)
	def visitUnaryPrefixOp(self, node):
		opname = opnames.unaryPrefixLUT[node.op]
		return self.directCall(node, exports['interpreter%s' % opname].code, None, [self(node.expr)])

	@dispatch(ast.GetGlobal)
	def visitGetGlobal(self, node):
		return self.directCall(node, exports['interpreterLoadGlobal'].code, None, [self(self.code.selfparam), self(node.name)])

	@dispatch(ast.GetIter)
	def visitGetIter(self, node):
		return self.directCall(node, exports['interpreter_iter'].code, None, [self(node.expr)])


	@dispatch(ast.BuildList)
	def visitBuildList(self, node):
		return self.directCall(node, exports['buildList'].code, None, self(node.args))

	@dispatch(ast.BuildTuple)
	def visitBuildTuple(self, node):
		return self.directCall(node, exports['buildTuple'].code, None, self(node.args))

	@dispatch(ast.UnpackSequence)
	def visitUnpackSequence(self, node):
		# HACK oh so ugly... does not resemble what actually happens.
		# HACK does not track rewriting, as it is single -> multi
		calls = []

		for i, arg in enumerate(node.targets):
			obj = self.extractor.getObject(i)
			call = self.directCall(arg, exports['interpreter_getitem'].code, None, [self(node.expr), self(ast.Existing(obj))])
			calls.append(ast.Assign(call, arg))

		return calls

	@dispatch(ast.GetAttr)
	def visitGetAttr(self, node):
		return self.directCall(node, exports['interpreter_getattribute'].code, None, [self(node.expr), self(node.name)])

	@dispatch(ast.SetAttr)
	def visitSetAttr(self, node):
		return ast.Discard(self.directCall(node, exports['interpreter_setattr'].code, None, [self(node.expr), self(node.name), self(node.value)]))

##	def visitWhile(self, node):
##		self.visit(node.condition)
##		self.visit(node.body)
##		if node.else_: self.visit(node.else_)
##
##	@dispatch(ast.For)
##	def visitFor(self, node):
##		iterator = self(node.iterator)
##
##		self.directCall(node.index, exports['interpreter_next'], None, [iterator])
##
##		self(node.body)
##
##		if node.else_:
##			self(node.else_)


def callConverter(extractor, adb, node):
	assert isinstance(node, ast.Code), node
	node.ast = ConvertCalls(extractor, adb, node)(node.ast)
	return node
