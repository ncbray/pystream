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
	if isinstance(node, ast.Function):
		node = node.code

	gl = GetLocals()
	gl(node)
	return gl.locals

class ShapeConstraintBuilder(object):
	__metaclass__ = typedispatcher

	def __init__(self, sys):
		self.sys = sys

		self.function = None
		self.uid = 0
		self.current  = (self.function, self.uid)

		self.statementPre = {}
		self.statementPost = {}

		self.constraints = []

		self.functionCallPoint   = {}
		self.functionReturnPoint = {}

		self.functionParams = {}
		self.functionLocals = {}
		self.functionLocalSlots = {}
		self.functionLocalExprs = {}

		self.returnPoint = None

	def setFunction(self, func):
		self.function = func
		self.current  = (func, self.current[1])

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

	def forget(self, lcl):
		self.forgetAll((lcl.slot,))

	def forgetAll(self, slots):
		pre = self.current
		post = self.advance()
		constraint = constraints.ForgetConstraint(self.sys, pre, post, frozenset(slots))
		self.constraints.append(constraint)

	def copy(self, src, dst):
		constraint = constraints.CopyConstraint(self.sys, src, dst)
		self.constraints.append(constraint)


	def makeCallerArgs(self, node, target):
		selfarg = self.localExpr(node.selfarg)
		args = [self.localExpr(arg) for arg in node.args]

		kwds = {}
		for kwd, lcl in node.kwds:
			kwds[kwd] = self.localExpr(lcl)

		vargs = self.localExpr(node.vargs)
		kargs = self.localExpr(node.kargs)

		if target is not None:
			returnarg = self.localExpr(target)
		else:
			returnarg = None

		callerargs = util.calling.CallerArgs(selfarg, args, kwds, vargs, kargs, returnarg)
		return callerargs


	def _makeCalleeParams(self, node):
		code = node.code
		selfparam = self.localExpr(code.selfparam)
		params = [self.localExpr(arg) for arg in code.parameters]
		paramnames = code.parameternames
		defaults = []

		vparam = self.localExpr(code.vparam)
		kparam = self.localExpr(code.kparam)
		returnparam = self.localExpr(code.returnparam)

		calleeparams = util.calling.CalleeParams(selfparam, params, paramnames, defaults, vparam, kparam, returnparam)
		return calleeparams


	def getCalleeParams(self, node):
		if node not in self.functionParams:
			params = self._makeCalleeParams(node)
			self.functionParams[node] = params
			return params
		else:
			return self.functionParams

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

	@dispatch(ast.DirectCall)
	def visitDirectCall(self, node, target):
		# TODO context sensitivity?
		invocations = self.sys.db.invocations(self.function, self.context, node)
		invocationMap = {self.context:invocations}

		callerargs = self.makeCallerArgs(node, target)

		pre = self.pre(node)
		post = self.advance()

		for dstFunc, dstContext in invocations:
			self.handleInvocation(pre, post, self.context, callerargs, dstFunc, dstContext)

		self.current = post
		self.post(node)

	def computeTransfer(self, callerargs, calleeparams):
		assert callerargs.vargs is None
		assert callerargs.kargs is None

		selfArg  = callerargs.selfarg is not None
		numVArgs = 0
		numArgs  = len(callerargs.args)+numVArgs
		info = util.calling.callStackToParamsInfo(calleeparams, selfArg, numArgs, False, callerargs.kwds.keys(), False)
		return info

	def mapArguments(self, callerargs, calleeparams, info):
		# HACK things not supported for this iteration
		assert not info.uncertainParam
		assert not info.uncertainVParam
		assert not info.certainKeywords
		assert not info.defaults

		# Self arg transfer
		if callerargs.selfarg and calleeparams.selfparam:
			self.assign(callerargs.selfarg, calleeparams.selfparam)

		# Arg to param transfer
		for argID, paramID in info.argParam:
			arg = callerargs.args[argID]
			param = calleeparams.params[paramID]
			#print arg, '->', param
			self.assign(arg, param)

		for argID, paramID in info.argVParam:
			assert False, "Can't handle vparams?"
			print argID, '->', paramID

	def handleInvocation(self, callPoint, returnPoint, srcContext, callerargs, dstFunc, dstContext):
		calleeparams = self.getCalleeParams(dstFunc)

		info = self.computeTransfer(callerargs, calleeparams)

		if info.willSucceed.mustBeFalse(): return

		# We may not know the program point for the function entry,
		# so defer linking until after all the functions have been processed.


		# HACK shouldn't be all locals pased to SplitMerge info, just the slots?
		splitMergeInfo = constraints.SplitMergeInfo(self.functionLocalExprs[dstFunc], self.functionLocalSlots[dstFunc])
		splitMergeInfo.srcLocals = self.functionLocalSlots[self.function]
		splitMergeInfo.dstLocals = self.functionLocalSlots[dstFunc]

		# Create a mapping to transfer the return value.
		returnSlot = calleeparams.returnparam.slot
		targetSlot = callerargs.returnarg.slot
		splitMergeInfo.mapping[targetSlot] = None
		splitMergeInfo.mapping[returnSlot] = targetSlot


		# Call invoke: split the information
		self.current = callPoint
		self.mapArguments(callerargs, calleeparams, info)

		# Make the constraint
		# TODO context sensitive copy?
		pre = self.current
		post = self.functionCallPoint[dstFunc]
		constraint = constraints.SplitConstraint(self.sys, pre, post, splitMergeInfo)
		self.constraints.append(constraint)

		# Call return: merge the information
		pre  = self.functionReturnPoint[dstFunc]
		post = returnPoint
		constraint = constraints.MergeConstraint(self.sys, pre, post, splitMergeInfo)
		self.constraints.append(constraint)

		self.current = returnPoint

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
		# This is not a forget, as it is replaced will a null
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


	@dispatch(ast.Function)
	def visitFunciton(self, node):
		pre = self.pre(node)

		self.returnValue = node.code.returnparam

		self.returnPoint = self.newID()

		self(node.code.ast)


		self.current = self.returnPoint

		if True:
			# Generate a kill constraint for the locals.
			returnSlot = self.sys.canonical.localSlot(node.code.returnparam)
			lcls = self.functionLocalSlots[self.function] - set((returnSlot,))
			self.forgetAll(lcls)

		post = self.post(node)



	def process(self, node):
		self.context  = None # HACK

		self.setFunction(node)

		self.functionLocals[node] =  frozenset(getLocals(node))

		# TODO these are slots, not expressions?
		self.functionLocalSlots[node] = frozenset([self.sys.canonical.localSlot(lcl) for lcl in self.functionLocals[node]])
		self.functionLocalExprs[node] = frozenset([self.sys.canonical.localExpr(lcl) for lcl in self.functionLocalSlots[node]])

		self.advance()

		self.functionCallPoint[node] = self.current
		self(node)
		self.functionReturnPoint[node] = self.current

		return self.statementPre[node], self.statementPost[node]
