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

	def process(self, node):
		# This function forces traversal of the node, even if it's shared.
		# Note that node may be an arbitrary AST node.
		if isinstance(node, ast.Local):
			self.locals.add(node)
		else:
			for child in node.children():
				self(child)
		return self.locals

def getLocals(node):
	return GetLocals().process(node)

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

		self.debug = False

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
		if self.debug:
			print "PRE"
			print node
			print self.current
			print

		self.statementPre[node] = self.current
		return self.current

	def post(self, node):
		if self.debug:
			print "POST"
			print node
			print self.current
			print

		self.statementPost[node] = self.current
		return self.current



	def localExpr(self, lcl):
		if lcl is not None:
			assert isinstance(lcl, (ast.Local, int)), lcl
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

		if self.debug:
			print "ASSIGN"
			print pre
			print post
			print


	def forget(self, lcl):
		self.forgetAll((lcl.slot,))

	def forgetAll(self, slots, post=None):
		pre = self.current

		if not post:
			post = self.advance()
		else:
			self.current = post

		constraint = constraints.ForgetConstraint(self.sys, pre, post, frozenset(slots))
		self.constraints.append(constraint)

		if self.debug:
			print "FORGET"
			print pre
			print post
			print

	def copy(self, src, dst):
		if self.debug:
			print "COPY"
			print src
			print dst
			print

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
		code = node
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
		selfArg  = callerargs.selfarg is not None

		numVArgs = 0
		vargsUncertain = bool(callerargs.vargs)

		assert callerargs.kargs is None

		numArgs  = len(callerargs.args)+numVArgs
		info = util.calling.callStackToParamsInfo(calleeparams, selfArg, numArgs, vargsUncertain, callerargs.kwds.keys(), False)
		return info

	def indexExpr(self, expr, index):
		field = self.sys.canonical.fieldSlot(None, ('Array', self.sys.extractor.getObject(index)))
		return self.sys.canonical.fieldExpr(expr, field)

	def maxVArgLength(self):
		# HACK arbitrarily transfer args
		# TODO figure out how many we should transfer.
		return 3

	def maxVParamLength(self):
		# HACK arbitrarily transfer args
		# TODO figure out how many we should transfer.
		return 3

	def mapArguments(self, callerargs, calleeparams, info):
		# HACK things not supported for this iteration
		#assert not info.uncertainParam
		#assert not info.uncertainVParam
		assert not info.certainKeywords
		assert not info.defaults

		paramSlots = set()

		# Self arg transfer
		# HACK
		assert not calleeparams.selfparam

		for i, arg in enumerate(callerargs.args):
			slot = self.sys.canonical.localSlot(i)
			expr = self.sys.canonical.localExpr(slot)

			self.assign(arg, expr)
			paramSlots.add(slot)

		base = len(callerargs.args)

		if callerargs.vargs:
			for i in range(self.maxVArgLength()):
				src = self.indexExpr(callerargs.vargs, i)

				slot = self.sys.canonical.localSlot(i+base)
				expr = self.sys.canonical.localExpr(slot)

				self.assign(src, expr)
				paramSlots.add(slot)

		assert not calleeparams.kparam

		return paramSlots

	def makeSplitMergeInfo(self, dstFunc, calleeparams, callerargs, parameterSlots):
		# We may not know the program point for the function entry,
		# so defer linking until after all the functions have been processed.

		splitMergeInfo = constraints.SplitMergeInfo(parameterSlots)
		splitMergeInfo.srcLocals = self.functionLocalSlots[self.function]
		splitMergeInfo.dstLocals = self.functionLocalSlots[dstFunc]

		# Create a mapping to transfer the return value.
		returnSlot = calleeparams.returnparam.slot
		targetSlot = callerargs.returnarg.slot
		splitMergeInfo.mapping[targetSlot] = None
		splitMergeInfo.mapping[returnSlot] = targetSlot

		return splitMergeInfo

	def makeSplit(self, dstFunc, splitMergeInfo):
		# TODO context sensitive copy?
		pre = self.current
		post = self.functionCallPoint[dstFunc]
		constraint = constraints.SplitConstraint(self.sys, pre, post, splitMergeInfo)
		self.constraints.append(constraint)

	def makeMerge(self, dstFunc, splitMergeInfo, returnPoint):
		# Call return: merge the information
		pre  = self.functionReturnPoint[dstFunc]
		post = returnPoint
		constraint = constraints.MergeConstraint(self.sys, pre, post, splitMergeInfo)
		self.constraints.append(constraint)

		self.current = returnPoint

	def handleInvocation(self, callPoint, returnPoint, srcContext, callerargs, dstFunc, dstContext):
		calleeparams = self.getCalleeParams(dstFunc)

		info = self.computeTransfer(callerargs, calleeparams)
		if info.willSucceed.mustBeFalse(): return

		# Do arg -> param mapping
		self.current = callPoint
		paramSlots = self.mapArguments(callerargs, calleeparams, info)

		# Make the constraints
		splitMergeInfo = self.makeSplitMergeInfo(dstFunc, calleeparams, callerargs, paramSlots)
		self.makeSplit(dstFunc, splitMergeInfo)
		self.makeMerge(dstFunc, splitMergeInfo, returnPoint)



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


	@dispatch(ast.Switch)
	def visitSwitch(self, node):
		pre = self.pre(node)

		self(node.condition)

		condOut = self.current

		self(node.t)
		tOut = self.current

		self.current = condOut

		self(node.f)
		fOut = self.current

		if tOut or fOut:
			self.advance()
			if tOut: self.copy(tOut, self.current)
			if fOut: self.copy(fOut, self.current)

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


	def transferParameters(self, node):
		# TODO self?

		forget = set()

		assert not node.selfparam


		# Assign positional params -> locals
		for i, param in enumerate(node.parameters):
			slot = self.sys.canonical.localSlot(i)
			expr = self.sys.canonical.localExpr(slot)

			self.assign(expr, self.localExpr(param))
			forget.add(slot)

		if node.vparam:
			vparam = self.localExpr(node.vparam)
			base = len(node.parameters)

			for i in range(self.maxVParamLength()):
				slot = self.sys.canonical.localSlot(i+base)
				expr = self.sys.canonical.localExpr(slot)

				dst = self.indexExpr(vparam, i)

				self.assign(expr, dst)
				forget.add(slot)

		assert not node.kparam


		if forget: self.forgetAll(forget)


	@dispatch(ast.Code)
	def visitCode(self, node):
		pre = self.pre(node)



		self.transferParameters(node)

		self.returnValue = node.returnparam
		self.returnPoint = self.newID()

		if self.debug:
			print "RETURN"
			print self.returnPoint
			print

		exitPoint = self.newID()

		self.functionCallPoint[node]   = pre
		self.functionReturnPoint[node] = exitPoint



		self(node.ast)


		self.current = self.returnPoint

		# Generate a kill constraint for the locals.
		returnSlot = self.sys.canonical.localSlot(node.returnparam)
		lcls = self.functionLocalSlots[self.function] - set((returnSlot,))
		self.forgetAll(lcls, exitPoint)

		post = self.post(node)

		assert post is exitPoint


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
