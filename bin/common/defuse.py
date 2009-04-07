import util.traversal as traversal
from util.visitor import StandardVisitor

import collections
from language.python.ast import Local, Existing, Cell, ASTNode, Statement, Assign, Suite

class CodeVisitor(traversal.ConcreteVisitor):
	def visit(self, node, args):
		if isinstance(node, (list, tuple)):
			return
		elif isinstance(node, ASTNode):
			self.om.disbatch(self, node, args)
		else:
			# Just for development.
			assert node==None or isinstance(node, (str, int, float))
			return


class DefUseVisitor(CodeVisitor):
	def __init__(self):
		self.lcldef 	= collections.defaultdict(list)
		self.lcluse 	= collections.defaultdict(list)

		self.globaldef 	= collections.defaultdict(list)
		self.globaluse	= collections.defaultdict(list)

		self.celldef 	= collections.defaultdict(list)
		self.celluse	= collections.defaultdict(list)


	def define(self, location, lcl):
		if isinstance(lcl, Local):
			self.lcldef[lcl].append(location)
		elif isinstance(lcl, Cell):
			self.celldef[lcl].append(location)
		else:
			assert False, (location, repr(lcl))


	def use(self, location, lcl):
		if isinstance(lcl, Local):
			self.lcluse[lcl].append(location)
		elif isinstance(lcl, Cell):
			self.celluse[lcl].append(location)
		elif lcl==None:
			pass
		else:
			pass #assert False, (location, lcl)

	def defineGlobal(self, location, gname):
		assert isinstance(gname, Existing)
		name = gname.constantValue()
		assert isinstance(name, str)
		self.globaldef[name].append(location)

	def useGlobal(self, location, gname):
		assert isinstance(gname, Existing)
		name = gname.constantValue()
		assert isinstance(name, str)
		self.globaluse[name].append(location)

	def visitLocal(self, node):
		pass

	def visitDelete(self, node):
		self.use(node, node.lcl)

	def visitExisting(self, node):
		pass

	def visitCell(self, node):
		pass


	def visitImport(self, node):
		pass

	def visitGetGlobal(self, node):
		# TODO use internal self?
		self.useGlobal(node, node.name)

	def visitSetGlobal(self, node):
		# TODO use internal self?
		self.defineGlobal(node, node.name)
		self.use(node, node.value)

	def visitDeleteGlobal(self, node):
		# TODO use internal self?
		self.defineGlobal(node, node.name)

	def visitSuite(self, node):
		pass

	def visitCode(self, node):
		if node.selfparam:
			self.define(node, node.selfparam)
		for param in node.parameters:
			self.define(node, param)
		if node.vparam:
			self.define(node, node.vparam)
		if node.kparam:
			self.define(node, node.kparam)


	def visitConvertToBool(self, node):
		self.use(node, node.expr)

	def visitUnaryPrefixOp(self, node):
		self.use(node, node.expr)

	def visitNot(self, node):
		self.use(node, node.expr)


	def visitYield(self, node):
		self.use(node, node.expr)

	def visitGetIter(self, node):
		self.use(node, node.expr)

	def visitBinaryOp(self, node):
		self.use(node, node.left)
		self.use(node, node.right)

	def handleArgs(self, node):
		for arg in node.args:
			self.use(node, arg)

		for name, arg in node.kwds:
			self.use(node, arg)

		if node.vargs:
			self.use(node, node.vargs)

		if node.kargs:
			self.use(node, node.kargs)

	def visitCall(self, node):
		self.use(node, node.expr)
		self.handleArgs(node)


	def visitDirectCall(self, node):
		if node.selfarg:
			self.use(node, node.selfarg)
		self.handleArgs(node)

	def visitMethodCall(self, node):
		self.use(node, node.expr)
		self.use(node, node.name)
		self.handleArgs(node)

	def visitBuildTuple(self, node):
		for arg in node.args:
			self.use(node, arg)

	def visitBuildMap(self, node):
		pass

	def visitBuildList(self, node):
		for arg in node.args:
			self.use(node, arg)


	def visitGetCell(self, node):
		self.use(node, node.cell)


	def visitGetCellDeref(self, node):
		self.use(node, node.cell)


	def visitSetCellDeref(self, node):
		self.define(node, node.cell)
		self.use(node, node.value)


	def visitSetAttr(self, node):
		self.use(node, node.value)
		self.use(node, node.expr)

	def visitGetAttr(self, node):
		self.use(node, node.expr)

	def visitDeleteAttr(self, node):
		self.use(node, node.expr)

	def visitBuildSlice(self, node):
		if node.start: self.use(node, node.start)
		if node.stop: self.use(node, node.stop)
		if node.step: self.use(node, node.step)

	def visitGetSlice(self, node):
		self.use(node, node.expr)

		if node.start: self.use(node, node.start)
		if node.stop: self.use(node, node.stop)
		if node.step: self.use(node, node.step)

	def visitSetSlice(self, node):
		self.use(node, node.value)
		self.use(node, node.expr)

		if node.start: self.use(node, node.start)
		if node.stop: self.use(node, node.stop)
		if node.step: self.use(node, node.step)


	def visitDeleteSlice(self, node):
		self.use(node, node.expr)

		if node.start: self.use(node, node.start)
		if node.stop: self.use(node, node.stop)
		if node.step: self.use(node, node.step)

	def visitSwitch(self, node):
		assert len(self.lcluse[node.condition]) == 0

	def visitCondition(self, node):
		self.use(node, node.conditional)

	def visitExceptionHandler(self, node):
		if node.type: self.use(node, node.type)
		if node.value: self.define(node, node.value)

	def visitShortCircutOr(self, node):
		pass

	def visitShortCircutAnd(self, node):
		pass

	def visitWhile(self, node):
		pass

	def visitTryExceptFinally(self, node):
		pass

	def visitFor(self, node):
		pass
		#assert len(self.lcluse[node.iterator]) == 0
		#self.define(node, node.index)
		#self.use(node, node.iterator)

	def visitBreak(self, node):
		pass

	def visitContinue(self, node):
		pass


	def visitGetSubscript(self, node):
		self.use(node, node.expr)
		self.use(node, node.subscript)

	def visitSetSubscript(self, node):
		self.use(node, node.value)
		self.use(node, node.expr)
		self.use(node, node.subscript)


	def visitDeleteSubscript(self, node):
		self.use(node, node.expr)
		self.use(node, node.subscript)

	def visitReturn(self, node):
		if not isinstance(node.expr, Existing):
			self.use(node, node.expr)

	def visitRaise(self, node):
		if node.exception: self.use(node, node.exception)
		if node.parameter: self.use(node, node.parameter)
		if node.traceback: self.use(node, node.traceback)

	def visitAssign(self, node):
		self.define(node, node.lcl)
		if isinstance(node.expr, Local):
			self.use(node, node.expr)

	def visitUnpackSequence(self, node):
		for lcl in node.targets:
			self.define(node, lcl)
		self.use(node, node.expr)

	def visitDiscard(self, node):
		if isinstance(node.expr, Local):
			# Sure, this node will be killed later, but until then it counts as a use.
			self.use(node, node.expr)

	def visitPrint(self, node):
		if node.target: self.use(node, node.target)
		if node.expr:  self.use(node, node.expr)

	def visitMakeFunction(self, node):
		#self.use(node, node.code)

		for default in node.defaults:
			self.use(node, default)

		for cell in node.cells:
			self.use(node, cell)

	def visitAllocate(self, node):
		self.use(node, node.expr)

	def visitLoad(self, node):
		self.use(node, node.expr)
		self.use(node, node.name)

	def visitStore(self, node):
		self.use(node, node.expr)
		self.use(node, node.name)
		self.use(node, node.value)

	def visitCheck(self, node):
		self.use(node, node.expr)
		self.use(node, node.name)

class Collapser(StandardVisitor):
	def __init__(self, defines, uses):
		self.defines	= defines
		self.uses 	= uses
		self.resetStack()

		self.collapsable = set()

	def resetStack(self):
		self.stack = []

	def markCollapsable(self, lcl):
		assert isinstance(lcl, Local)
		# Multiple uses for an existing object is ok.
		if len(self.defines[lcl]) == 1 and len(self.uses[lcl]) >= 1:
			self.collapsable.add(lcl)

	def markPossible(self, *args):
		for arg in args:
			if arg == None:
				continue
			elif isinstance(arg, Local):
				# Can we collapse it?
				# Only a single use for a non-constant is acceptable.
				if len(self.uses[arg]) == 1:
					self.stack.append(arg)
			else:
				self.process(arg)

	def process(self, node):
		if node == None:
			return

		if isinstance(node, Statement) and not isinstance(node, Assign) and not isinstance(node, Suite):
			self.resetStack()

##		for assign in reversed(node.onExit):
##			self.process(assign)

		self.visit(node)

##		for assign in reversed(node.onEntry):
##			self.process(assign)

	def visitCode(self, node):
		self.process(node.ast)

	def visitSuite(self, node):
		for block in reversed(node.blocks):
			self.process(block)

	def visitReturn(self, node):
		self.process(node.expr)

		if not isinstance(node.expr, Existing):
			self.markPossible(node.expr)

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

	def visitBreak(self, node):
		pass

	def visitContinue(self, node):
		pass

	def visitLocal(self, node):
		pass

	def visitExisting(self, node):
		pass

	def visitCell(self, node):
		pass


	def visitConvertToBool(self, node):
		self.handleUnaryExpr(node)

	def visitYield(self, node):
		self.handleUnaryExpr(node)

	def visitCondition(self, node):
		self.resetStack()
		self.markPossible(node.conditional)
		#self.process(node.conditional)
		self.process(node.preamble)

	def visitExceptionHandler(self, node):
		self.resetStack()
		self.process(node.body)

		self.resetStack()
		if node.value: self.process(node.value)

		if node.type:
			self.process(node.type)
			self.markPossible(node.type)

		self.process(node.preamble)


	def visitShortCircutOr(self, node):
		for term in reversed(node.terms):
			self.resetStack()
			self.process(term)

	def visitShortCircutAnd(self, node):
		for term in reversed(node.terms):
			self.resetStack()
			self.process(term)


	def visitSwitch(self, node):
		self.resetStack()
		self.process(node.f)

		self.resetStack()
		self.process(node.t)

		self.resetStack()
		self.process(node.condition)

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

	def visitWhile(self, node):
		if node.else_:
			self.resetStack()
			self.process(node.else_)

		self.resetStack()
		self.process(node.body)
		self.resetStack()
		self.process(node.condition)
		self.resetStack()

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

	def visitAssign(self, node):
		if isinstance(node.expr, Existing):
			# Can reorder and duplicate without penalty
			# Should have already optimized out, however?
			self.markCollapsable(node.lcl)
		elif isinstance(node.expr, Local):
			# TODO is this sound?
			self.searchForTargetNondestructive(node.lcl)
			self.markPossible(node.expr)
		else:
			self.searchForTarget(node.lcl)
			self.process(node.expr)

	def visitDelete(self, node):
		self.resetStack()

	def visitImport(self, node):
		self.resetStack()

	def visitDiscard(self, node):
		if not node.expr.isReference():
			# May have side effects, but cannot be collapsed.
			# As such, nothing can collapse past this statement, so clear the "possible" stack.
			self.resetStack()
			self.process(node.expr)

	def visitBinaryOp(self, node):
		self.process(node.right)
		self.process(node.left)
		self.markPossible(node.left, node.right)



	def visitUnaryPrefixOp(self, node):
		self.handleUnaryExpr(node)

	def visitGetIter(self, node):
		self.handleUnaryExpr(node)

	def handleUnaryExpr(self, node):
		self.process(node.expr)
		self.markPossible(node.expr)

	def visitNot(self, node):
		self.process(node.expr)
		self.markPossible(node.expr)



	def visitGetAttr(self, node):
		self.process(node.expr)
		self.markPossible(node.expr)

	def visitSetAttr(self, node):
		self.process(node.value)
		self.process(node.expr)

		# TODO reset stack?

		self.markPossible(node.expr, node.value)

	def visitDeleteAttr(self, node):
		self.process(node.expr)
		self.markPossible(node.expr)

	def visitGetCell(self, node):
		self.process(node.cell)

	def visitGetCellDeref(self, node):
		self.process(node.cell)


	def visitSetCellDeref(self, node):
		self.process(node.value)
		self.markPossible(node.value)


	def visitGetGlobal(self, node):
		self.process(node.name)

	def visitSetGlobal(self, node):
		#self.process(node.name)
		self.process(node.value)

		# TODO reset stack?

		self.markPossible(node.value)

	def visitDeleteGlobal(self, node):
		self.resetStack()
		self.process(node.name)

	def visitGetSubscript(self, node):
		self.process(node.subscript)
		self.process(node.expr)
		self.markPossible(node.expr, node.subscript)

	def visitSetSubscript(self, node):
		self.process(node.subscript)
		self.process(node.expr)
		self.process(node.value)

		# TODO reset stack?

		self.markPossible(node.value, node.expr, node.subscript)


	def visitDeleteSubscript(self, node):
		self.resetStack()

		self.process(node.subscript)
		self.process(node.expr)

		self.markPossible(node.expr, node.subscript)


	def visitBuildSlice(self, node):
		if node.step: self.process(node.step)
		if node.stop: self.process(node.stop)
		if node.start: self.process(node.start)

		if node.start: self.markPossible(node.start)
		if node.stop: self.markPossible(node.stop)
		if node.step: self.markPossible(node.step)

	def visitGetSlice(self, node):
		if node.step: self.process(node.step)
		if node.stop: self.process(node.stop)
		if node.start: self.process(node.start)
		self.process(node.expr)

		self.markPossible(node.expr)
		if node.start: self.markPossible(node.start)
		if node.stop: self.markPossible(node.stop)
		if node.step: self.markPossible(node.step)


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

	def visitBuildTuple(self, node):
		for arg in reversed(node.args):
			self.process(arg)

		self.markPossible(*node.args)

	def visitBuildMap(self, node):
		pass

	def visitUnpackSequence(self, node):
		self.resetStack()
		self.markPossible(node.expr)

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

	def visitCall(self, node):
		self.processArgs(node)
		self.process(node.expr)
		self.markPossible(node.expr)
		self.markArgs(node)


	def visitDirectCall(self, node):
		self.processArgs(node)

		if node.selfarg:
			self.process(node.selfarg)
			self.markPossible(node.selfarg)

		self.markArgs(node)

	def visitMethodCall(self, node):
		self.processArgs(node)

		self.process(node.name)
		self.process(node.expr)
		self.markPossible(node.expr)
		self.markPossible(node.name)

		self.markArgs(node)

	def visitPrint(self, node):
		if node.expr: self.process(node.expr)
		if node.target: self.process(node.target)

		if node.target: self.markPossible(node.target)
		if node.expr: self.markPossible(node.expr)


	def visitMakeFunction(self, node):
		for arg in reversed(node.defaults):
			self.process(arg)

		#self.process(node.code)

		#self.markPossible(node.code)
		self.markPossible(*node.defaults)
		#self.markPossible(*node.cells)

	def visitAllocate(self, node):
		self.process(node.expr)
		self.markPossible(node.expr)

	def visitLoad(self, node):
		self.process(node.name)
		self.process(node.expr)
		self.markPossible(node.expr, node.name)

	def visitStore(self, node):
		self.process(node.value)
		self.process(node.name)
		self.process(node.expr)
		self.markPossible(node.expr, node.name, node.value)

	def visitCheck(self, node):
		self.process(node.name)
		self.process(node.expr)
		self.markPossible(node.expr, node.name)

def defuse(ast):
	duv = DefUseVisitor()
	visitor = traversal.DFS(duv, traversal.Identity())
	visitor.setObjectModel(traversal.DefaultObjectModel())

	visitor.visit(ast, ())


	c = Collapser(duv.lcldef, duv.lcluse)
	c.walk(ast)


	return (duv.lcldef, duv.lcluse), (duv.globaldef, duv.globaluse), c.collapsable
