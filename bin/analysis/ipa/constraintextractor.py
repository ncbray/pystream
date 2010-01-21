from util.typedispatch import *
from language.python import ast, program

from . constraints import *

class MarkParameters(TypeDispatcher):
	def __init__(self, ce):
		self.ce = ce

	@dispatch(type(None))
	def visitNone(self, node):
		pass

	@dispatch(ast.Local)
	def visitLocal(self, node):
		self.ce(node).markParam()

	def process(self, codeParameters):
		self(codeParameters.selfparam)
		for param in codeParameters.params:
			self(param)

		self(codeParameters.vparam)
		self(codeParameters.kparam)

		for param in codeParameters.returnparams:
			self.ce(param).markReturn()

class ConstraintExtractor(TypeDispatcher):
	def __init__(self, analysis, context):
		self.analysis = analysis
		self.context  = context

	@dispatch(ast.leafTypes)
	def visitLeaf(self, node):
		return node

	@dispatch(ast.Local)
	def visitLocal(self, node):
		return self.context.local(node)

	@dispatch(ast.Existing)
	def visitExisting(self, node):
		xtype = self.analysis.canonical.existingType(node.object)
		return self.analysis.object(xtype, True)

	def call(self, node, expr, args, kwds, vargs, kargs, targets):
		assert not kwds, self.code
		assert kargs is None, self.code

		self.context.call(expr, args, kwds, vargs, kargs, targets)

	def dcall(self, node, code, expr, args, kwds, vargs, kargs, targets):
		assert not kwds, self.code
		assert kargs is None, self.code

		self.context.dcall(code, expr, args, kwds, vargs, kargs, targets)

	def allocate(self, node, expr, targets):
		assert expr.isObject(), expr
		assert len(targets) == 1

		inst = expr.name.obj.typeinfo.abstractInstance
		xtype = self.analysis.canonical.pathType(self.context.signature, inst, node)
		co = self.analysis.object(xtype, False)

		self.context.assign(co, targets[0])

	def load(self, node, expr, fieldtype, name, targets):
		assert len(targets) == 1
		self.context.constraint(LoadConstraint(self.wrap(expr), fieldtype, self.wrap(name), targets[0]))

	def wrap(self, cn):
		if cn.isObject():
			lc = self.context.local(ast.Local('wrap'))
			self.context.assign(cn, lc)
			return lc
		else:
			return cn

	@dispatch(ast.Call)
	def visitCall(self, node, targets):
		return self.call(node, self(node.expr),
			self(node.args), self(node.kwds),
			self(node.vargs), self(node.kargs), targets)

	@dispatch(ast.DirectCall)
	def visitDirectCall(self, node, targets):
		return self.dcall(node, node.code, self(node.selfarg),
			self(node.args), self(node.kwds),
			self(node.vargs), self(node.kargs), targets)

	@dispatch(ast.Allocate)
	def visitAllocate(self, node, targets):
		return self.allocate(node, self(node.expr), targets)

	@dispatch(ast.Load)
	def visitLoad(self, node, targets):
		return self.load(node, self(node.expr), node.fieldtype, self(node.name), targets)

	@dispatch(ast.Assign)
	def visitAssign(self, node):
		self(node.expr, self(node.lcls))

	@dispatch(ast.Discard)
	def visitDiscard(self, node):
		self(node.expr, None)

	@dispatch(ast.Return)
	def visitReturn(self, node):
		assert len(node.exprs) == len(self.codeParameters.returnparams)

		exprs = self(node.exprs)
		params = self(self.codeParameters.returnparams)
		for expr, param in zip(exprs, params):
			self.context.assign(expr, param)

	@dispatch(list, tuple)
	def visitList(self, node):
		return [self(child) for child in node]

	@dispatch(ast.Suite)
	def visitOK(self, node):
		node.visitChildren(self)

	### Entry point ###
	def process(self):
		code =  self.context.signature.code
		self.codeParameters = code.codeParameters()

		MarkParameters(self).process(self.codeParameters)

		if code.isStandardCode():
			self(code.ast)
		else:
			code.extractConstraints(self)
