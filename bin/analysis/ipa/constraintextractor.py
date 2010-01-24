from util.typedispatch import *
from language.python import ast, program
from . model import objectname
from . constraints import qualifiers
from . constraints import flow

class MarkParameters(TypeDispatcher):
	def __init__(self, ce):
		self.ce = ce

	@dispatch(type(None), ast.DoNotCare)
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
	def visitLocal(self, node, targets=None):
		lcl = self.context.local(node)

		if targets is None:
			return lcl
		else:
			assert len(targets) == 1
			self.context.assign(lcl, targets[0])

	def existingObject(self, node):
		xtype = self.analysis.canonical.existingType(node.object)
		return self.analysis.object(xtype, qualifiers.GLBL)

	@dispatch(ast.Existing)
	def visitExisting(self, node, targets=None):
		obj = self.existingObject(node)
		lcl = self.context.local(ast.Local('existing_temp'))
		lcl.updateSingleValue(obj)
		if targets is None:
			return lcl
		else:
			assert len(targets) == 1
			self.context.assign(lcl, targets[0])

	def call(self, node, expr, args, kwds, vargs, kargs, targets):
		assert not kwds, self.code
		assert kargs is None, self.code

		self.context.call(node, expr, args, kwds, vargs, kargs, targets)

	def dcall(self, node, code, expr, args, kwds, vargs, kargs, targets):
		assert not kwds, self.code
		assert kargs is None, self.code

		self.context.dcall(node, code, expr, args, kwds, vargs, kargs, targets)

	def allocate(self, node, expr, targets):
		assert isinstance(expr, objectname.ObjectName), expr
		assert len(targets) == 1
		target = targets[0]

		obj = self.context.allocate(expr, node)

		# TODO lazy target creation?
		target.updateSingleValue(obj)

	def load(self, node, expr, fieldtype, name, targets):
		assert len(targets) == 1
		self.context.constraint(flow.LoadConstraint(expr, fieldtype, name, targets[0]))

	def check(self, node, expr, fieldtype, name, targets):
		assert len(targets) == 1
		self.context.constraint(flow.CheckConstraint(self.context, expr, fieldtype, name, targets[0]))

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
		return self.allocate(node, self.existingObject(node.expr), targets)

	@dispatch(ast.Load)
	def visitLoad(self, node, targets):
		return self.load(node, self(node.expr), node.fieldtype, self(node.name), targets)

	@dispatch(ast.Check)
	def visitCheck(self, node, targets):
		return self.check(node, self(node.expr), node.fieldtype, self(node.name), targets)

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

	@dispatch(ast.Suite, ast.Condition, ast.Switch)
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
