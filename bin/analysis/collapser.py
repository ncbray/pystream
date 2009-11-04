from asttools.transform import *
from language.python import ast

class Collapser(TypeDispatcher):
	def __init__(self, defines, uses):
		self.defines	= defines
		self.uses 	= uses
		self.resetStack()

		self.collapsable = set()

	def resetStack(self):
		self.stack = []

	def markCollapsable(self, lcl):
		assert isinstance(lcl, ast.Local)
		# Multiple uses for an existing object is ok.
		if len(self.defines[lcl]) == 1 and len(self.uses[lcl]) >= 1:
			self.collapsable.add(lcl)

	def markPossible(self, *args):
		for arg in args:
			if arg == None:
				continue
			elif isinstance(arg, ast.Local):
				# Can we collapse it?
				# Only a single use for a non-constant is acceptable.
				if len(self.uses[arg]) == 1:
					self.stack.append(arg)
			else:
				self.process(arg)

	def process(self, node):
		if node == None:
			return

		if isinstance(node, ast.Statement) and not isinstance(node, ast.Assign) and not isinstance(node, ast.Suite):
			self.resetStack()

		self(node)

	@dispatch(ast.Suite)
	def visitSuite(self, node):
		visitAllChildrenReversed(self.process, node.blocks)

	@dispatch(ast.Return)
	def visitReturn(self, node):
		visitAllChildrenReversed(self.process, node.exprs)

		for expr in node.exprs:
			if not isinstance(expr, ast.Existing):
				self.markPossible(expr)

	@dispatch(ast.Raise)
	def visitRaise(self, node):
		if node.exception:
			if node.parameter:
				if node.traceback:
					self.process(node.traceback)
				self.process(node.parameter)
			self.process(node.exception)

		if node.exception:
			self.markPossible(node.exception)
			if node.parameter:
				self.markPossible(node.parameter)
				if node.traceback:
					self.markPossible(node.traceback)

	@dispatch(ast.Break, ast.Continue, ast.Local, ast.Existing, ast.Cell, ast.DoNotCare)
	def visitNOP(self, node):
		pass

	@dispatch(ast.ConvertToBool)
	def visitConvertToBool(self, node):
		self.handleUnaryExpr(node)

	@dispatch(ast.Yield)
	def visitYield(self, node):
		self.handleUnaryExpr(node)

	@dispatch(ast.Condition)
	def visitCondition(self, node):
		self.resetStack()
		self.markPossible(node.conditional)
		#self.process(node.conditional)
		self.process(node.preamble)

	@dispatch(ast.ExceptionHandler)
	def visitExceptionHandler(self, node):
		self.resetStack()
		self.process(node.body)

		self.resetStack()
		if node.value: self.process(node.value)

		if node.type:
			self.process(node.type)
			self.markPossible(node.type)

		self.process(node.preamble)

	@dispatch(ast.ShortCircutOr, ast.ShortCircutAnd)
	def visitShortCircut(self, node):
		for term in reversed(node.terms):
			self.resetStack()
			self.process(term)

	@dispatch(ast.Switch)
	def visitSwitch(self, node):
		self.resetStack()
		self.process(node.f)

		self.resetStack()
		self.process(node.t)

		self.resetStack()
		self.process(node.condition)

	@dispatch(ast.TypeSwitchCase)
	def visitTypeSwitchCase(self, node):
		self.process(node.body)

	@dispatch(ast.TypeSwitch)
	def visitTypeSwitch(self, node):
		for case in reversed(node.cases):
			self.resetStack()
			self.process(case)
		self.resetStack()
		self.process(node.conditional)

	@dispatch(ast.TryExceptFinally)
	def visitTryExceptFinally(self, node):
		if node.finally_:
			self.resetStack()
			self.process(node.finally_)

		if node.else_:
			self.resetStack()
			self.process(node.else_)

		if node.defaultHandler:
			self.resetStack()
			self.process(node.defaultHandler)

		for handler in reversed(node.handlers):
			self.resetStack()
			self.process(handler)

		self.resetStack()
		self.process(node.body)

	@dispatch(ast.While)
	def visitWhile(self, node):
		if node.else_:
			self.resetStack()
			self.process(node.else_)

		self.resetStack()
		self.process(node.body)
		self.resetStack()
		self.process(node.condition)
		self.resetStack()

	@dispatch(ast.For)
	def visitFor(self, node):
		# Preambles are ignored, as they're "internal"
		if node.else_:
			self.resetStack()
			self.process(node.else_)

		self.resetStack()
		self.process(node.body)
		self.resetStack()
		self.process(node.iterator)
		self.markPossible(node.iterator)

		# Make sure the iterator can be collapsed.
		# It's not nessisary, but it should occur if everything is working correctly.
		#assert self.stack and self.stack[-1] == node.iterator, (node.iterator, self.stack)

		# Def/use is a little bit strange when the preambles are considered.
		# As such, we can't guarentee the iterator will be able to collapse.

	def searchForTarget(self, lcl):
		# See if anyone is looking for this local.
		while self.stack:
			current = self.stack.pop()
			if current == lcl:
				self.markCollapsable(lcl)
				break
		else:
			# Functionally unessisary, exits for illustration.
			# If we can't collapse this operation, no operations can collapse past it.
			self.resetStack()

	def searchForTargetNondestructive(self, lcl):
		if lcl in self.stack:
			self.markCollapsable(lcl)

	@dispatch(ast.Assign)
	def visitAssign(self, node):
		if isinstance(node.expr, ast.Existing):
			# Can reorder and duplicate without penalty
			# Should have already optimized out, however?
			assert len(node.lcls) == 1
			self.markCollapsable(node.lcls[0])
		elif isinstance(node.expr, ast.Local):
			# TODO is this sound?
			assert len(node.lcls) == 1
			self.searchForTargetNondestructive(node.lcls[0])
			self.markPossible(node.expr)
		else:
			if len(node.lcls) == 1:
				self.searchForTarget(node.lcls[0])
			else:
				self.resetStack()
			self.process(node.expr)

	@dispatch(ast.Delete)
	def visitDelete(self, node):
		self.resetStack()

	@dispatch(ast.Import)
	def visitImport(self, node):
		self.resetStack()

	@dispatch(ast.Discard)
	def visitDiscard(self, node):
		if not node.expr.isReference():
			# May have side effects, but cannot be collapsed.
			# As such, nothing can collapse past this statement, so clear the "possible" stack.
			self.resetStack()
			self.process(node.expr)

	@dispatch(ast.BinaryOp, ast.Is)
	def visitBinaryOp(self, node):
		self.process(node.right)
		self.process(node.left)
		self.markPossible(node.left, node.right)

	@dispatch(ast.UnaryPrefixOp)
	def visitUnaryPrefixOp(self, node):
		self.handleUnaryExpr(node)

	@dispatch(ast.GetIter)
	def visitGetIter(self, node):
		self.handleUnaryExpr(node)

	def handleUnaryExpr(self, node):
		self.process(node.expr)
		self.markPossible(node.expr)

	@dispatch(ast.Not)
	def visitNot(self, node):
		self.process(node.expr)
		self.markPossible(node.expr)


	@dispatch(ast.GetAttr)
	def visitGetAttr(self, node):
		self.process(node.expr)
		self.markPossible(node.expr)

	@dispatch(ast.SetAttr)
	def visitSetAttr(self, node):
		self.process(node.value)
		self.process(node.expr)

		# TODO reset stack?

		self.markPossible(node.expr, node.value)

	@dispatch(ast.DeleteAttr)
	def visitDeleteAttr(self, node):
		self.process(node.expr)
		self.markPossible(node.expr)

	@dispatch(ast.GetCell, ast.GetCellDeref)
	def visitGetCell(self, node):
		self.process(node.cell)


	@dispatch(ast.SetCellDeref)
	def visitSetCellDeref(self, node):
		self.process(node.value)
		self.markPossible(node.value)

	@dispatch(ast.GetGlobal)
	def visitGetGlobal(self, node):
		self.process(node.name)

	@dispatch(ast.SetGlobal)
	def visitSetGlobal(self, node):
		#self.process(node.name)
		self.process(node.value)

		# TODO reset stack?

		self.markPossible(node.value)

	@dispatch(ast.DeleteGlobal)
	def visitDeleteGlobal(self, node):
		self.resetStack()
		self.process(node.name)

	@dispatch(ast.GetSubscript)
	def visitGetSubscript(self, node):
		self.process(node.subscript)
		self.process(node.expr)
		self.markPossible(node.expr, node.subscript)

	@dispatch(ast.SetSubscript)
	def visitSetSubscript(self, node):
		self.process(node.subscript)
		self.process(node.expr)
		self.process(node.value)

		# TODO reset stack?

		self.markPossible(node.value, node.expr, node.subscript)

	@dispatch(ast.DeleteSubscript)
	def visitDeleteSubscript(self, node):
		self.resetStack()

		self.process(node.subscript)
		self.process(node.expr)

		self.markPossible(node.expr, node.subscript)

	@dispatch(ast.BuildSlice)
	def visitBuildSlice(self, node):
		if node.step: self.process(node.step)
		if node.stop: self.process(node.stop)
		if node.start: self.process(node.start)

		if node.start: self.markPossible(node.start)
		if node.stop: self.markPossible(node.stop)
		if node.step: self.markPossible(node.step)

	@dispatch(ast.GetSlice)
	def visitGetSlice(self, node):
		if node.step: self.process(node.step)
		if node.stop: self.process(node.stop)
		if node.start: self.process(node.start)
		self.process(node.expr)

		self.markPossible(node.expr)
		if node.start: self.markPossible(node.start)
		if node.stop: self.markPossible(node.stop)
		if node.step: self.markPossible(node.step)

	@dispatch(ast.SetSlice)
	def visitSetSlice(self, node):
		if node.step: self.process(node.step)
		if node.stop: self.process(node.stop)
		if node.start: self.process(node.start)
		self.process(node.expr)
		self.process(node.value)

		self.markPossible(node.value, node.expr)
		if node.start: self.markPossible(node.start)
		if node.stop: self.markPossible(node.stop)
		if node.step: self.markPossible(node.step)

	@dispatch(ast.DeleteSlice)
	def visitDeleteSlice(self, node):
		self.resetStack()

		if node.step: self.process(node.step)
		if node.stop: self.process(node.stop)
		if node.start: self.process(node.start)
		self.process(node.expr)

		self.markPossible(node.expr)
		if node.start: self.markPossible(node.start)
		if node.stop: self.markPossible(node.stop)
		if node.step: self.markPossible(node.step)

	@dispatch(ast.BuildTuple)
	def visitBuildTuple(self, node):
		for arg in reversed(node.args):
			self.process(arg)

		self.markPossible(*node.args)

	@dispatch(ast.BuildMap)
	def visitBuildMap(self, node):
		pass

	@dispatch(ast.UnpackSequence)
	def visitUnpackSequence(self, node):
		self.resetStack()
		self.markPossible(node.expr)

	@dispatch(ast.BuildList)
	def visitBuildList(self, node):
		for arg in reversed(node.args):
			self.process(arg)

		self.markPossible(*node.args)

	def processArgs(self, node):
		if node.kargs:
			self.process(node.kargs)

		if node.vargs:
			self.process(node.vargs)

		for name, arg in reversed(node.kwds):
			self.process(arg)

		for arg in reversed(node.args):
			self.process(arg)

	def markArgs(self, node):
		self.markPossible(*node.args)
		for name, arg in reversed(node.kwds):
			self.markPossible(arg)
		if node.vargs:
			self.markPossible(node.vargs)

		if node.kargs:
			self.markPossible(node.kargs)

	@dispatch(ast.Call)
	def visitCall(self, node):
		self.processArgs(node)
		self.process(node.expr)
		self.markPossible(node.expr)
		self.markArgs(node)

	@dispatch(ast.DirectCall)
	def visitDirectCall(self, node):
		self.processArgs(node)

		if node.selfarg:
			self.process(node.selfarg)
			self.markPossible(node.selfarg)

		self.markArgs(node)

	@dispatch(ast.MethodCall)
	def visitMethodCall(self, node):
		self.processArgs(node)

		self.process(node.name)
		self.process(node.expr)
		self.markPossible(node.expr)
		self.markPossible(node.name)

		self.markArgs(node)

	@dispatch(ast.Print)
	def visitPrint(self, node):
		if node.expr: self.process(node.expr)
		if node.target: self.process(node.target)

		if node.target: self.markPossible(node.target)
		if node.expr: self.markPossible(node.expr)

	@dispatch(ast.MakeFunction)
	def visitMakeFunction(self, node):
		for arg in reversed(node.defaults):
			self.process(arg)

		#self.process(node.code)

		#self.markPossible(node.code)
		self.markPossible(*node.defaults)
		#self.markPossible(*node.cells)

	@dispatch(ast.Allocate)
	def visitAllocate(self, node):
		self.process(node.expr)
		self.markPossible(node.expr)

	@dispatch(ast.Load)
	def visitLoad(self, node):
		self.process(node.name)
		self.process(node.expr)
		self.markPossible(node.expr, node.name)

	@dispatch(ast.Store)
	def visitStore(self, node):
		self.process(node.value)
		self.process(node.name)
		self.process(node.expr)
		self.markPossible(node.expr, node.name, node.value)

	@dispatch(ast.Check)
	def visitCheck(self, node):
		self.process(node.name)
		self.process(node.expr)
		self.markPossible(node.expr, node.name)


	@dispatch(ast.Code)
	def visitCode(self, node):
		self.process(node.ast)


def evaluateCode(compiler, code, defs, uses):
	c = Collapser(defs, uses)
	c(code)
	return c.collapsable