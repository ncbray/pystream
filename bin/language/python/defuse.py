from util.typedispatch import *
from language.python import ast

import collections

class DFS(object):
	def __init__(self, pre):
		self.pre = pre
		self.visited = set()

	def visit(self, node, force=False):
		if isinstance(node, ast.Code):
			if node in self.visited:
				return
			else:
				self.visited.add(node)

		self.pre(node)

		# Don't recurse on leaf nodes
		if isinstance(node, ast.leafTypes): return

		# Recurse

		# HACK we must analyze the code inside MakeFunction
		doForce = isinstance(node, ast.MakeFunction)
		if force or doForce:
			node.visitChildrenForcedArgs(self.visit, doForce)
		else:
			node.visitChildren(self.visit)

	def process(self, node):
		# Force the traversal of the entry point.
		self.visit(node, force=True)


class DefUseVisitor(TypeDispatcher):
	def __init__(self):
		TypeDispatcher.__init__(self)

		self.lcldef 	= collections.defaultdict(list)
		self.lcluse 	= collections.defaultdict(list)

		self.globaldef 	= collections.defaultdict(list)
		self.globaluse	= collections.defaultdict(list)

		self.celldef 	= collections.defaultdict(list)
		self.celluse	= collections.defaultdict(list)


	def define(self, location, lcl):
		if isinstance(lcl, ast.Local):
			self.lcldef[lcl].append(location)
		elif isinstance(lcl, ast.DoNotCare):
			pass
		elif isinstance(lcl, ast.Cell):
			self.celldef[lcl].append(location)
		else:
			assert False, (location, repr(lcl))


	def use(self, location, lcl):
		if isinstance(lcl, ast.Local):
			self.lcluse[lcl].append(location)
		elif isinstance(lcl, ast.DoNotCare):
			pass
		elif isinstance(lcl, ast.Cell):
			self.celluse[lcl].append(location)
		elif lcl==None:
			pass
		else:
			pass #assert False, (location, lcl)

	def defineGlobal(self, location, gname):
		assert isinstance(gname, ast.Existing)
		name = gname.constantValue()
		assert isinstance(name, str)
		self.globaldef[name].append(location)

	def useGlobal(self, location, gname):
		assert isinstance(gname, ast.Existing)
		name = gname.constantValue()
		assert isinstance(name, str)
		self.globaluse[name].append(location)

	@dispatch(ast.Delete)
	def visitDelete(self, node):
		self.use(node, node.lcl)

	@dispatch(ast.GetGlobal)
	def visitGetGlobal(self, node):
		# TODO use internal self?  Difficult, as defuse may analyize multiple code in a single pass
		self.useGlobal(node, node.name)

	@dispatch(ast.SetGlobal)
	def visitSetGlobal(self, node):
		# TODO use internal self?  Difficult, as defuse may analyize multiple code in a single pass
		self.defineGlobal(node, node.name)
		self.use(node, node.value)

	@dispatch(ast.DeleteGlobal)
	def visitDeleteGlobal(self, node):
		# TODO use internal self?
		self.defineGlobal(node, node.name)

	@dispatch(ast.CodeParameters)
	def visitCodeParameters(self, node):
		if node.selfparam:
			self.define(node, node.selfparam)
		for param in node.params:
			self.define(node, param)
		if node.vparam:
			self.define(node, node.vparam)
		if node.kparam:
			self.define(node, node.kparam)

	@dispatch(ast.UnaryPrefixOp, ast.Not, ast.Yield, ast.GetIter, ast.ConvertToBool)
	def visitUnary(self, node):
		self.use(node, node.expr)

	@dispatch(ast.BinaryOp, ast.Is)
	def visitBinaryOp(self, node):
		self.use(node, node.left)
		self.use(node, node.right)

	@dispatch(ast.Assert)
	def visitAssert(self, node):
		self.use(node, node.test)
		self.use(node, node.message)

	def handleArgs(self, node):
		for arg in node.args:
			self.use(node, arg)

		for name, arg in node.kwds:
			self.use(node, arg)

		if node.vargs:
			self.use(node, node.vargs)

		if node.kargs:
			self.use(node, node.kargs)

	@dispatch(ast.Call)
	def visitCall(self, node):
		self.use(node, node.expr)
		self.handleArgs(node)

	@dispatch(ast.DirectCall)
	def visitDirectCall(self, node):
		if node.selfarg:
			self.use(node, node.selfarg)
		self.handleArgs(node)

	@dispatch(ast.MethodCall)
	def visitMethodCall(self, node):
		self.use(node, node.expr)
		self.use(node, node.name)
		self.handleArgs(node)

	@dispatch(ast.BuildTuple, ast.BuildList)
	def visitBuildContainer(self, node):
		for arg in node.args:
			self.use(node, arg)

	@dispatch(ast.GetCell)
	def visitGetCell(self, node):
		self.use(node, node.cell)

	@dispatch(ast.GetCellDeref)
	def visitGetCellDeref(self, node):
		self.use(node, node.cell)

	@dispatch(ast.SetCellDeref)
	def visitSetCellDeref(self, node):
		self.define(node, node.cell)
		self.use(node, node.value)

	@dispatch(ast.SetAttr)
	def visitSetAttr(self, node):
		self.use(node, node.value)
		self.use(node, node.expr)
		self.use(node, node.name)

	@dispatch(ast.GetAttr)
	def visitGetAttr(self, node):
		self.use(node, node.expr)
		self.use(node, node.name)

	@dispatch(ast.DeleteAttr)
	def visitDeleteAttr(self, node):
		self.use(node, node.expr)
		self.use(node, node.name)

	@dispatch(ast.BuildSlice)
	def visitBuildSlice(self, node):
		if node.start: self.use(node, node.start)
		if node.stop: self.use(node, node.stop)
		if node.step: self.use(node, node.step)

	@dispatch(ast.GetSlice)
	def visitGetSlice(self, node):
		self.use(node, node.expr)

		if node.start: self.use(node, node.start)
		if node.stop: self.use(node, node.stop)
		if node.step: self.use(node, node.step)

	@dispatch(ast.SetSlice)
	def visitSetSlice(self, node):
		self.use(node, node.value)
		self.use(node, node.expr)

		if node.start: self.use(node, node.start)
		if node.stop: self.use(node, node.stop)
		if node.step: self.use(node, node.step)

	@dispatch(ast.DeleteSlice)
	def visitDeleteSlice(self, node):
		self.use(node, node.expr)

		if node.start: self.use(node, node.start)
		if node.stop: self.use(node, node.stop)
		if node.step: self.use(node, node.step)

	@dispatch(ast.Switch)
	def visitSwitch(self, node):
		assert len(self.lcluse[node.condition]) == 0

	@dispatch(ast.Condition)
	def visitCondition(self, node):
		self.use(node, node.conditional)

	@dispatch(ast.TypeSwitchCase)
	def visitTypeSwitchCase(self, node):
		self.define(node, node.expr)

	@dispatch(ast.TypeSwitch)
	def visitTypeSwitch(self, node):
		self.use(node, node.conditional)

	@dispatch(ast.ExceptionHandler)
	def visitExceptionHandler(self, node):
		if node.type: self.use(node, node.type)
		if node.value: self.define(node, node.value)

	@dispatch(ast.Break, ast.Continue, ast.For, ast.While, ast.TryExceptFinally,
		ast.ShortCircutAnd, ast.ShortCircutOr,
		ast.Local, ast.DoNotCare, ast.Existing, ast.Cell, ast.Import, ast.Suite,
		ast.Code, ast.BuildMap,
		ast.leafTypes, list, tuple)
	def visitLeaf(self, node):
		pass

	@dispatch(ast.GetSubscript)
	def visitGetSubscript(self, node):
		self.use(node, node.expr)
		self.use(node, node.subscript)

	@dispatch(ast.SetSubscript)
	def visitSetSubscript(self, node):
		self.use(node, node.value)
		self.use(node, node.expr)
		self.use(node, node.subscript)


	@dispatch(ast.DeleteSubscript)
	def visitDeleteSubscript(self, node):
		self.use(node, node.expr)
		self.use(node, node.subscript)

	@dispatch(ast.Return)
	def visitReturn(self, node):
		for expr in node.exprs:
			if not isinstance(expr, ast.Existing):
				self.use(node, expr)

	@dispatch(ast.InputBlock)
	def visitInputBlock(self, node):
		for input in node.inputs:
			self.define(node, input.lcl)

	@dispatch(ast.OutputBlock)
	def visitOutputBlock(self, node):
		for output in node.outputs:
			if not isinstance(output.expr, ast.Existing):
				self.use(node, output.expr)


	@dispatch(ast.Input, ast.Output, ast.IOName)
	def visitOutput(self, node):
		pass

	@dispatch(ast.Raise)
	def visitRaise(self, node):
		if node.exception: self.use(node, node.exception)
		if node.parameter: self.use(node, node.parameter)
		if node.traceback: self.use(node, node.traceback)

	@dispatch(ast.Assign)
	def visitAssign(self, node):
		for lcl in node.lcls:
			self.define(node, lcl)

		if isinstance(node.expr, ast.Local):
			self.use(node, node.expr)

	@dispatch(ast.UnpackSequence)
	def visitUnpackSequence(self, node):
		for lcl in node.targets:
			self.define(node, lcl)
		self.use(node, node.expr)

	@dispatch(ast.Discard)
	def visitDiscard(self, node):
		if isinstance(node.expr, ast.Local):
			# Sure, this node will be killed later, but until then it counts as a use.
			self.use(node, node.expr)

	@dispatch(ast.Print)
	def visitPrint(self, node):
		if node.target: self.use(node, node.target)
		if node.expr:  self.use(node, node.expr)

	@dispatch(ast.MakeFunction)
	def visitMakeFunction(self, node):
		#self.use(node, node.code)

		for default in node.defaults:
			self.use(node, default)

		for cell in node.cells:
			self.use(node, cell)

	@dispatch(ast.Allocate)
	def visitAllocate(self, node):
		self.use(node, node.expr)

	@dispatch(ast.Load)
	def visitLoad(self, node):
		self.use(node, node.expr)
		self.use(node, node.name)

	@dispatch(ast.Store)
	def visitStore(self, node):
		self.use(node, node.expr)
		self.use(node, node.name)
		self.use(node, node.value)

	@dispatch(ast.Check)
	def visitCheck(self, node):
		self.use(node, node.expr)
		self.use(node, node.name)


def evaluateCode(compiler, code):
	duv = DefUseVisitor()
	visitor = DFS(duv)
	visitor.process(code)

	return (duv.lcldef, duv.lcluse), (duv.globaldef, duv.globaluse)
