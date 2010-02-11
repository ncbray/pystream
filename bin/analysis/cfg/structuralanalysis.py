from util.typedispatch import *
from language.python import ast
from . import graph, dom

class Search(object):
	def __init__(self):
		self.processed = set()
		self.current = set()
		self.loops = set()

		self.order = []

	def process(self, node):
		if node not in self.processed:
			self.current.add(node)
			self.processed.add(node)

			for child in node.forward():
				self.process(child)

			self.order.append(node)
			self.current.remove(node)
		elif node in self.current:
			self.loops.add(node)


class KillContinues(TypeDispatcher):
	@dispatch(ast.leafTypes, ast.Condition, ast.While, ast.Break, ast.Assign, ast.Discard)
	def visitLeaf(self, node):
		return node

	@dispatch(ast.Switch)
	def visitSwitch(self, node):
		return node.rewriteChildren(self)

	@dispatch(ast.Continue)
	def visitContinue(self, node):
		return []

	@dispatch(ast.Suite)
	def visitSuite(self, node):
		if len(node.blocks) > 1:
			return ast.Suite(node.blocks[:-1]+[self(node.blocks[-1])])
		else:
			return node

class Compactor(TypeDispatcher):
	def __init__(self, compiler, g, loops):
		self.compiler = compiler
		self.g = g
		self.loops = loops

		normal = self.g.normalTerminal

		np = normal.prev
		if isinstance(np, graph.Merge):
			self.returns = (np, normal)
		else:
			self.returns = (normal,)


		self.breaks = {}

	def isReturnNode(self, node):
		return node in self.returns

	def caseMerge(self, case):
		if isinstance(case, graph.Merge):
			return case
		else:
			return case.getExit('normal')

	def getSwitchExit(self, node, name, ignoreRegion=False):
		next = node.getExit(name)

		assert next is not None

		if isinstance(next, graph.Merge) or (not ignoreRegion and next.region is not node.region):
			next = graph.Suite(node.region)
			node.insertAtExit(name, next, 'normal')

			self.simplifySuite(next)

		return next

	def getCommonExit(self, *suites):
		allexit = None

		for suite in suites:
			argexit = suite.getExit('normal')
			if argexit:
				if allexit:
					if allexit is not argexit:
						return False, None
				else:
					allexit = argexit

		return True, allexit


	@dispatch(graph.Switch)
	def visitSwitch(self, node):
		t = self.getSwitchExit(node, 'true')
		f = self.getSwitchExit(node, 'false', ignoreRegion=True)

		if node.region is not t.region or node.region is not f.region:
			return

		ok, exit = self.getCommonExit(t, f)
		if not ok: return

		ok, error = self.getError(t, f)
		if not ok: return

		condition = ast.Condition(ast.Suite([]), node.condition)
		switch = ast.Switch(condition, ast.Suite(t.ops), ast.Suite(f.ops))

		result = graph.Suite(node.region)
		result.ops.append(switch)


		# Reconnect the graph

		node.redirectEntries(result)
		t.destroy()
		f.destroy()

		if exit:
			result.setExit('normal', exit)
			if isinstance(exit, graph.Merge):
				exit.simplify()

		if error:
			result.setExit('error', error)

		self.simplifySuite(result)

	@dispatch(graph.TypeSwitch)
	def visitTypeSwitch(self, node):
		exits = [self.getSwitchExit(node, i) for i in range(len(node.original.cases))]


		for e in exits:
			assert node.region is e.region


		ok, exit = self.getCommonExit(*exits)
		assert ok

		ok, error = self.getError(*exits)
		assert ok


		cases = [ast.TypeSwitchCase(case.types, case.expr, ast.Suite(e.ops)) for case, e in zip(node.original.cases, exits)]

		switch = ast.TypeSwitch(node.original.conditional, cases)

		result = graph.Suite(node.region)
		result.ops.append(switch)


		# Reconnect the graph

		node.redirectEntries(result)
		for e in exits:
			e.destroy()

		if exit:
			result.setExit('normal', exit)
			if isinstance(exit, graph.Merge):
				exit.simplify()

		if error:
			result.setExit('error', error)

		self.simplifySuite(result)

	def getError(self, *args):
		error = None

		for arg in args:
			argerror = arg.getExit('error')
			if error:
				if error is not argerror:
					return False, None
			else:
				argerror = error

		return True, error

	def simplifySuite(self, node):
		while True:
			next = node.getExit('normal')

			if next is None:
				break
			elif isinstance(next, graph.Suite) and node.region is next.region:
				ok, error = self.getError(node, next)
				if not ok: break

				if not node.getExit('error'):
					node.setExit('error', error)

				node.ops.extend(next.ops)

				node.forwardExit(next, 'normal')
			elif self.isReturnNode(next):
				node.killExit('normal')
				break
			elif next is node.region:
				# Continue
				node.ops.append(ast.Continue())
				node.killExit('normal')
				break
			elif node.region and next.region is node.region.region:
				# Could be a break
				if node.region not in self.breaks:
					self.breaks[node.region] = next
				else:
					assert self.breaks[node.region] is next, "Inconsistent loop breaks."

				node.ops.append(ast.Break())
				node.killExit('normal')
				break
			else:
				break

	@dispatch(graph.Merge)
	def visitMerge(self, node):
		if node not in self.loops:
			node.simplify()
		else:
			assert node.numPrev() == 1

			preamble = node.getExit('normal')

			if isinstance(preamble, graph.Switch):
				assert False
			else:
				assert isinstance(preamble, graph.Suite)

			switch = preamble.getExit('normal')

#			print
#			print preamble.ops
#			print switch

			if switch is None:
				# Degenerate loop
				body = preamble

				preamble = graph.Suite(body.region)

				switch = graph.Switch(body.region, ast.Existing(self.compiler.extractor.getObject(True)))

				else_ = graph.Suite(body.region)
			else:
				assert isinstance(switch, graph.Switch)

				body  = self.getSwitchExit(switch, 'true')
				else_ = self.getSwitchExit(switch, 'false', ignoreRegion=True)

				switch.killExit('true')
				switch.killExit('false')

#			print
#			print "pre", preamble.ops
#			print "cond", switch.condition
#			print "body", body.ops
#			print "else", else_.ops

			if node in self.breaks:
				b = self.breaks[node]
				ee = else_.getExit('normal')
				assert ee is None or ee is b
				else_.killExit('normal')

			else:
				b = else_
				else_ = graph.Suite(else_.region)

#			print
#			print "pre", preamble.ops
#			print "cond", switch.condition
#			print "body", body.ops
#			print "else", else_.ops
#			print "break", b.ops

			bodyast = ast.Suite(body.ops)
			bodyast = KillContinues()(bodyast)

			loop = ast.While(ast.Condition(ast.Suite(preamble.ops), switch.condition), bodyast, ast.Suite(else_.ops))

			result = graph.Suite(node.region)
			result.ops.append(loop)

			node.killExit('normal')
			node.setExit('normal', result)

			result.setExit('normal', b)

			if isinstance(b, graph.Merge):
				b.simplify()

			node.simplify()

			#print list(result.forward())

			self.simplifySuite(result)

			#print list(result.forward())


			preamble.destroy()
			switch.destroy()
			body.destroy()
			else_.destroy()


	@dispatch(graph.Suite)
	def visitSuite(self, node):
		self.simplifySuite(node)

	@dispatch(graph.Exit, graph.Entry)
	def visitTerminal(self, node):
		pass

def processLoop(dj):
	assert len(dj.d) == 1

	switch = dj.d[0]

	if isinstance(switch.node, graph.Suite):
		assert len(switch.d) == 1, [d.node for d in switch.d]
		switch = switch.d[0]

	assert isinstance(switch.node, graph.Switch), switch.node

def findLoops(dj):
	if isinstance(dj.node, graph.Merge):
		for prev in dj.node.reverse():
			if dj.dominates(prev.data):
				processLoop(dj)

	for d in dj.d:
		findLoops(d)

def evaluate(compiler, g):
	def forward(node):
		return node.normalForward()

	def bind(node, djnode):
		node.data = djnode

	dom.evaluate([g.entryTerminal], forward, bind)

	djroot = g.entryTerminal.data

	findLoops(djroot)

	s = Search()
	s.process(g.entryTerminal)

	order = s.order

	c = Compactor(compiler, g, s.loops)

	for node in order:
		c(node)

	entry = g.entryTerminal

	body = entry.getExit('entry')

	assert body.getExit('normal') is None, "could not reduce?"


	g.code.ast = ast.Suite(body.ops)
