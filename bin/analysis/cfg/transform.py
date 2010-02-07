from util.typedispatch import *
from . import simplify, dump

from language.python import ast
from . import graph as cfg

NoNormalFlow = cfg.NoNormalFlow

class CFGTransformer(TypeDispatcher):
	def emit(self, stmt):
		self.current.ops.append(stmt)

	def attachCurrent(self, child):
		if not self.current.ops:
			# Avoid creating empty nodes
			self.current.redirectEntries(child)
		else:
			self.current.setExit('normal', child)
		self.current = None

	def flowReturn(self):
		assert self.current is not None
		self.attachCurrent(self.handler('return'))
		raise NoNormalFlow

	@dispatch(ast.Return)
	def visitReturn(self, node):
		self.emit(node)
		self.flowReturn()

	@dispatch(ast.Continue)
	def visitContinue(self, node):
		assert self.current is not None
		self.attachCurrent(self.handler('continue'))
		raise NoNormalFlow

	@dispatch(ast.Break)
	def visitBreak(self, node):
		assert self.current is not None
		self.attachCurrent(self.handler('break'))
		raise NoNormalFlow

	@dispatch(ast.Yield)
	def visitYield(self, node):
		y = cfg.Yield()
		self.attachCurrent(y)
		y.setExit('normal', self.makeNewSuite())

	@dispatch(ast.Assign, ast.Discard, ast.SetAttr, ast.UnpackSequence)
	def visitStatement(self, node):
		self.emit(node)

	def createSwitchAfter(self, condition, prev):
		switch = cfg.Switch(self.region, condition)
		self.attachStandardHandlers(switch)
		prev.setExit('normal', switch)
		return switch

	def createMerge(self):
		merge = cfg.Merge(self.region)
		#self.attachStandardHandlers(merge)
		return merge

#	@dispatch(ast.Not)
#	def visitNot(self, node):
#		fail = cfg.Merge()
#		self.pushHandler('fail', fail)
#
#		suite  = cfg.Suite()
#		self.attachStandardHandlers(suite)
#		self.attachCurrent(suite)
#		self.current = suite
#
#		try:
#			try:
#				self(node.stmt)
#			finally:
#				self.popHandler('fail')
#		except NoNormalFlow:
#			pass
#		else:
#			self.current.setExit('normal', self.handler('fail'))
#
#		if fail.numPrev() == 0:
#			# No failiures
#			raise NoNormalFlow
#		else:
#			self.makeNewSuite()
#			fail.setExit('normal', self.current)

	@dispatch(ast.Switch)
	def visitIf(self, node):
		self(node.condition.preamble)
		switch = cfg.Switch(self.region, node.condition.conditional)
		self.attachStandardHandlers(switch)

		self.attachCurrent(switch)

		merges = []

		switch.setExit('true', self.makeNewSuite())
		try:
			self(node.t)
		except NoNormalFlow:
			pass
		else:
			merges.append(self.current)

		switch.setExit('false', self.makeNewSuite())
		try:
			self(node.f)
		except NoNormalFlow:
			pass
		else:
			merges.append(self.current)

		if len(merges) == 2:
			merge = self.createMerge()
			merges[0].setExit('normal', merge)
			merges[1].setExit('normal', merge)

			self.makeNewSuite()
			merge.setExit('normal', self.current)
		elif len(merges) == 1:
			self.current = merges[0]
		else:
			raise NoNormalFlow

	@dispatch(ast.While)
	def visitWhile(self, node):
		c  = self.createMerge()
		self.attachCurrent(c)


		b = cfg.Merge(self.region)
		e = cfg.Merge(self.region)

		self.pushRegion(c)

		c.setExit('normal', self.makeNewSuite())
		self(node.condition.preamble)

		switch = self.createSwitchAfter(node.condition.conditional, self.current)
		switch.setExit('true', self.makeNewSuite())


		self.pushHandler('continue', c)
		self.pushHandler('break', b)

		try:
			self(node.body)
		except NoNormalFlow:
			pass
		else:
			self.attachCurrent(c)

		self.popHandler('continue')
		self.popHandler('break')
		self.popRegion()

		switch.setExit('false', e)

		try:
			e.setExit('normal', self.makeNewSuite())
			self(node.else_)
		except NoNormalFlow:
			pass
		else:
			self.attachCurrent(b)

		b.setExit('normal', self.makeNewSuite())
		self.optimizeMerge(c)
		self.optimizeMerge(b)
		self.optimizeMerge(e)


	@dispatch(ast.For)
	def visitFor(self, node):
		self(node.initialize)

		merge  = self.createMerge()
		self.attachCurrent(merge)

		switch = self.createSwitchAfter(node.condition, merge)

		# Next iteration logic
		c = self.createMerge()
		c.setExit('normal', self.makeNewSuite())
		self(node.next)
		self.attachCurrent(merge)

		switch.setExit('true', self.makeNewSuite())

		b = cfg.Merge()

		self.pushHandler('continue', c)
		self.pushHandler('break', b)

		try:
			self(node.body)
		except NoNormalFlow:
			pass
		else:
			self.attachCurrent(c)

		self.popHandler('continue')
		self.popHandler('break')

		switch.setExit('false', b)

		b.setExit('normal', self.makeNewSuite())
		self.optimizeMerge(c)
		self.optimizeMerge(b)

	def optimizeMerge(self, m):
		m.simplify()

	@dispatch(ast.Suite)
	def visitSuite(self, node):
		assert self.current
		node.visitChildren(self)

	def pushHandler(self, name, node):
		assert isinstance(node, cfg.Merge)
		self.handlers[name].append(node)

	def popHandler(self, name):
		return self.handlers[name].pop()

	def handler(self, name):
		return self.handlers[name][-1]

	def attachStandardHandlers(self, node):
		node.setExit('fail', self.handler('fail'))
		node.setExit('error', self.handler('error'))

	def makeNewSuite(self):
		self.current  = cfg.Suite(self.region)
		self.attachStandardHandlers(self.current)
		return self.current

	def mergeInto(self, node):
		m = cfg.Merge(self.region)
		m.setExit('normal', node)
		return m

	def pushRegion(self, region):
		self.regionStack.append(self.region)
		self.region = region

	def popRegion(self):
		self.region = self.regionStack.pop()

	def process(self, code):
		self.regionStack = []
		self.region = None

		self.handlers = {'return':[], 'fail':[], 'error':[], 'continue':[], 'break':[]}

		self.code = cfg.Code()
		self.code.code = code

		self.pushHandler('return', self.mergeInto(self.code.normalTerminal))
		self.pushHandler('fail',   self.mergeInto(self.code.failTerminal))
		self.pushHandler('error',  self.mergeInto(self.code.errorTerminal))

		self.code.entryTerminal.setExit('entry', self.makeNewSuite())

		try:
			self(code.ast)
			self.flowReturn()
		except NoNormalFlow:
			pass

		self.popHandler('return')
		self.popHandler('fail')
		self.popHandler('error')

		return self.code

def evaluate(compiler, code):
	cfg = CFGTransformer().process(code)

	simplify.evaluate(compiler, cfg)

	return cfg
