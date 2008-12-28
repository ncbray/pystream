from __future__ import absolute_import

from util.typedispatch import *
from programIR.python import ast
from util import xform

from . model import expressions
from . import constraints

import util.calling

class GetLocals(object):
	__metaclass__ = typedispatcher

	def __init__(self):
		self.locals = set()

	@defaultdispatch
	def default(self, node):
		xform.visitAllChildren(self, node)

	@dispatch(ast.Local)
	def visitLocal(self, node):
		self.locals.add(node)

def getLocals(node):
	gl = GetLocals()
	gl(node)
	return gl.locals

class ShapeConstraintBuilder(object):
	__metaclass__ = typedispatcher

	def __init__(self, sys):
		self.sys = sys
		
		self.uid = 0
		self.current  = None

		self.statementPre = {}
		self.statementPost = {}

		self.constraints = []

		self.functionCall   = {}
		self.functionReturn = {}

		self.functionParams = {}

		self.returnPoint = None

	def newID(self):
		uid = self.uid
		self.uid += 1
		return (self.function, uid)

	def advance(self):
		uid = self.newID()
		self.current = uid
		return uid

	def pre(self, node):
		self.statementPre[node] = self.current
		return self.current

	def post(self, node):
		self.statementPost[node] = self.current
		return self.current



	def localExpr(self, lcl):
		if lcl is not None:
			assert isinstance(lcl, ast.Local), lcl
			slot = self.sys.canonical.localSlot(lcl)
			return self.sys.canonical.localExpr(slot)
		else:
			return None

	def fieldExpr(self, expr, field):
		slot = self.sys.canonical.fieldSlot(None, field)
		return self.sys.canonical.fieldExpr(self.localExpr(expr), slot)

	def assign(self, source, destination):
		pre = self.current
		post = self.advance()
		constraint = constraints.AssignmentConstraint(self.sys, pre, post, source, destination)
		self.constraints.append(constraint)

	def copy(self, src, dst):
		constraint = constraints.CopyConstraint(self.sys, src, dst)
		self.constraints.append(constraint)

	@defaultdispatch
	def default(self, node, *args):
		assert False, node

	@dispatch(ast.Suite)
	def visitSuite(self, node):
		self.pre(node)
		for child in node.blocks:
			self(child)
		self.post(node)
	
	@dispatch(ast.Assign)
	def visitAssign(self, node):
		self.pre(node)
		self(node.expr, node.lcl)
		self.post(node)


	@dispatch(ast.Discard)
	def visitDiscard(self, node):
		self.pre(node)
		self(node.expr, None)
		self.post(node)

	@dispatch(ast.Local)
	def visitLocal(self, node, target):
		self.assign(self.localExpr(node), self.localExpr(target))

	def makeCallerArgs(self, node):
		selfarg = self.localExpr(node.selfarg)
		args = [self.localExpr(arg) for arg in node.args]

		kwds = {}
		for kwd, lcl in node.kwds:
			kwds[kwd] = self.localExpr(lcl)

		vargs = self.localExpr(node.vargs)
		kargs = self.localExpr(node.kargs)

		callerargs = util.calling.CallerArgs(selfarg, args, kwds, vargs, kargs)
		return callerargs

	@dispatch(ast.DirectCall)
	def visitDirectCall(self, node, target):
		# TODO context sensitivity?
		invoke = self.sys.db.invocations(self.function, self.context, node)
		invocations = {self.context:invoke}

		callerargs = self.makeCallerArgs(node)

		
		target = self.localExpr(target)


		pre = self.pre(node)
		post = self.advance()
		
		constraint = constraints.CallConstraint(self.sys, pre, post, invocations, callerargs, target)
		self.constraints.append(constraint)

		self.post(node)


	@dispatch(ast.Load)
	def visitLoad(self, node, target):
		field = (node.fieldtype, node.name.object)
		self.assign(self.fieldExpr(node.expr, field), self.localExpr(target))

	@dispatch(ast.Store)
	def visitStore(self, node):
		self.pre(node)
		field        = (node.fieldtype, node.name.object)
		self.assign(self.localExpr(node.value), self.fieldExpr(node.expr, field))
		self.post(node)

	@dispatch(ast.Delete)
	def visitDelete(self, node):
		self.pre(node)		
		# HACK should also create a pointer to a null object.
		lcl = node.lcl		
		self.assign(expressions.null, self.localExpr(node.lcl))
		self.post(node)


	
	@dispatch(ast.Return)
	def visitReturn(self, node):
		pre = self.pre(node)
		
		constraint = constraints.AssignmentConstraint(self.sys, pre, self.returnPoint, self.localExpr(node.expr), self.localExpr(self.returnValue))
		self.constraints.append(constraint)

		self.current = None
		self.post(node)

	@dispatch(ast.Condition)
	def visitCondition(self, node):
		self.pre(node)
		# HACK ignoring the conditional
		self(node.preamble)
		self.post(node)


	@dispatch(ast.While)
	def visitWhile(self, node):
		pre = self.pre(node)

		condIn = self.advance()
		self(node.condition)
		condOut = self.current

		# HACK should use stack
		self.breakPoint = self.newID()
		self.continuePoint = condIn


		bodyIn = self.advance()
		self(node.body)
		bodyOut = self.current

		elseIn = self.advance()
		self(node.else_)
		elseOut = self.current


		self.current = self.breakPoint

		# Merge into the condition
		self.copy(pre, condIn)
		self.copy(bodyOut, condIn)

		# Split out of the condition
		self.copy(condOut, bodyIn)
		self.copy(condOut, elseIn)

		# Merge the breaks and the else
		self.copy(elseOut, self.breakPoint)

		# HACK should use stack
		self.breakPoint    = None
		self.continuePoint = None

		self.post(node)

##	@dispatch(ast.Code)
##	def visitCode(self, node):
##		# HACK
##		body = self(node.ast)


	def makeCalleeParams(self, node):
		selfparam = self.localExpr(node.selfparam)
		params = [self.localExpr(arg) for arg in node.parameters]
		paramnames = node.parameternames
		defaults = []

		vparam = self.localExpr(node.vparam)
		kparam = self.localExpr(node.kparam)

		calleeparams = util.calling.CalleeParams(selfparam, params, paramnames, defaults, vparam, kparam)
		return calleeparams
		

	@dispatch(ast.Function)
	def visitFunciton(self, node):
		self.function = node
		self.returnValue = node.code.returnparam

		pre = self.advance()
		self.pre(node)
		self.functionCall[node] = pre

		self.returnPoint = self.newID()
		
		self(node.code.ast)


		self.current = self.returnPoint

		# Generate a kill constraint for the locals.
		lcls = getLocals(node.code)
		lcls.remove(node.code.returnparam)
		lcls = [self.sys.canonical.localExpr(self.sys.canonical.localSlot(lcl)) for lcl in lcls]

		for lcl in lcls:
			self.assign(expressions.null, lcl)

		post = self.post(node)

		self.functionReturn[node] = self.current

		self.functionParams[node] = self.makeCalleeParams(node.code)


	def process(self, node):
		self.function = None
		self.context  = None # HACK
		self(node)
		return self.statementPre[node], self.statementPost[node]
