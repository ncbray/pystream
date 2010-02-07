from util.typedispatch import *
from language.python import ast

import collections

class ForwardDataflow(TypeDispatcher):
	def makeSymbolic(self, node):
		entry = (node, 'entry')
		exit  = (node, 'exit')

		self.entry[node] = entry
		self.exit[node] = exit

		return entry, exit

	def makeConcrete(self, node):
		entry = node
		exit  = node
		self.entry[node] = entry
		self.exit[node] = exit
		return entry, exit

	def link(self, prev, next):
		self._link(self.exit[prev], self.entry[next])

	def _link(self, prev, next):
		if prev is not None:
			self.next[prev].append(next)


	@dispatch(ast.Assign, ast.Discard, ast.Store, ast.OutputBlock)
	def visitStatement(self, node):
		entry, exit = self.makeConcrete(node)

	@dispatch(ast.Return)
	def visitReturn(self, node):
		self.entry[node] = node
		self.exit[node]  = None

		self._link(node, self.returnExit)

	@dispatch(ast.Condition)
	def visitCondition(self, node):
		# HACKISH?
		entry, exit = self.makeSymbolic(node)

		self(node.preamble)

		self._link(entry, self.entry[node.preamble])
		self._link(self.exit[node.preamble], exit)


	@dispatch(ast.Switch)
	def visitSwitch(self, node):
		entry, exit = self.makeSymbolic(node)

		self(node.condition)
		self(node.t)
		self(node.f)

		self._link(entry, self.entry[node.condition])

		self.link(node.condition, node.t)
		self.link(node.condition, node.f)

		self._link(self.exit[node.t], exit)
		self._link(self.exit[node.f], exit)

	@dispatch(ast.TypeSwitch)
	def visitTypeSwitch(self, node):
		entry, exit = self.makeSymbolic(node)

		# TODO conditional?

		for case in node.cases:
			self(case.body)
			self._link(entry, self.entry[case.body])
			self._link(self.exit[case.body], exit)

	@dispatch(ast.For)
	def visitFor(self, node):
		# HACKISH?

		entry, exit = self.makeSymbolic(node)

		self(node.loopPreamble)
		self(node.bodyPreamble)
		self(node.body)
		self(node.else_)

		self._link(entry, self.entry[node.loopPreamble])
		self.link(node.loopPreamble, node.bodyPreamble)
		self.link(node.bodyPreamble, node.body)
		self.link(node.body, node.bodyPreamble)
		self.link(node.body, node.else_)
		self._link(self.exit[node.else_], exit)

		# Nothing to iterate?
		self.link(node.loopPreamble, node.else_)


	@dispatch(ast.While)
	def visitWhile(self, node):
		# HACKISH?

		entry, exit = self.makeSymbolic(node)

		self(node.condition)
		self(node.body)
		self(node.else_)

		self._link(entry, self.entry[node.condition])
		self.link(node.condition, node.body)
		self.link(node.body, node.condition)
		self.link(node.condition, node.else_)
		self._link(self.exit[node.else_], exit)



	@dispatch(ast.Suite)
	def visitSuite(self, node):
		entry, exit = self.makeSymbolic(node)

		prev = entry
		for child in node.blocks:
			self(child)
			self._link(prev, self.entry[child])
			prev = self.exit[child]

		self._link(prev, exit)

	def processCode(self, code):
		self.next = collections.defaultdict(list)
		self.entry = {}
		self.exit  = {}

		entry, exit = self.makeSymbolic(code)

		self.returnExit = exit

		self(code.ast)

		self._link(entry, self.entry[code.ast])
		self._link(self.exit[code.ast], exit)

		return self.next
