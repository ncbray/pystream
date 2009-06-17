from base import *
from language.python import fold


# TODO structure like forward flow
# TODO merge in 'raise' when may raise.
# TODO integrate with decompiler?
# No flow control after raise issues?


class ReverseFlowTraverse(TypeDispatcher):
	__slots__ = 'strategy', 'meet', 'flow', 'mayRaise'

	def __init__(self, meetF, strategy):
		self.strategy = strategy
		self.meet = meetF

		self.mayRaise = MayRaise()

		# Assume there are contours for "return" and "raise"
		self.flow = FlowDict()
		self.flow.save('return')
		self.flow.restore(DynamicDict())
		self.flow.save('raise')

	@defaultdispatch
	def default(self, node):
		result = self.strategy(node)

		if self.flow.tryLevel > 0 and self.mayRaise(result):
			# Inject flow from exception handling
			assert len(self.flow.bags['raise']) == 1
			raiseF = self.flow.bags['raise'][0]
			normalF = self.flow.pop()
			normalF, changed = meet(self.meet, normalF, raiseF)
			self.flow.restore(normalF)

		return result

	@dispatch(ast.Suite, list, tuple, type(None))
	def visitFlow(self, node):
		node = xform.allChildrenReversed(self, node)
		return node

	@dispatch(ast.Condition)
	def visitCondition(self, node):
		self.strategy.marker(node.conditional)
		preamble = self(node.preamble)
		node = ast.Condition(preamble, node.conditional)
		return node

	# HACK
	@dispatch(ast.ExceptionHandler)
	def visitExceptionHandler(self, node):
		body = self(node.body)

		if node.value:
			self.flow.undefine(node.value)

		self.strategy.marker(node.type)

		preamble = self(node.preamble)

		node = ast.ExceptionHandler(preamble, node.type, node.value, body)
		return node


	@dispatch(ast.Switch)
	def visitSwitch(self, node):
		newNode = fold.foldSwitch(node)
		if newNode is not node: return self(newNode)


		# Split
		tf, ff = self.flow.popSplit()

		self.flow.restore(tf)
		t = self(node.t)
		tf = self.flow.pop()

		self.flow.restore(ff)
		f = self(node.f)
		ff = self.flow.pop()

		# Merge
		merged, changed = meet(self.meet, tf, ff)
		self.flow.restore(merged)

		condition = self(node.condition)

		return ast.Switch(condition, t, f)


	@dispatch(ast.While)
	def visitWhile(self, node):
		normalF, breakF = self.flow.popSplit()

		self.flow.restore(normalF)
		else_ = self(node.else_)
		inital = self.flow.pop()

		# Save the old loop points, and set new ones.
		oldBreak = self.flow.bags.get('break', [])
		self.flow.bags['break'] = [breakF]
		oldContinue = self.flow.bags.get('continue', [])


		# Iterate until convergence

		current = inital.split()
		while 1:
			# TODO undef the index?
			self.flow.bags['continue'] = [current.split()]
			self.flow.restore(current.split())

			condition = self(node.condition)
			body = self(node.body)

			loopEntry = self.flow.pop()
			current, changed = meet(self.meet, current, loopEntry)

			if not changed:
				break


		self.flow.restore(current)

		# Restore the loop points
		self.flow.bags['break'] = oldBreak
		self.flow.bags['continue'] = oldContinue

		condition = self(node.condition)

		return ast.While(condition, body, else_)



	@dispatch(ast.For)
	def visitFor(self, node):
		normalF, breakF = self.flow.popSplit()

		self.flow.restore(normalF)
		else_ = self(node.else_)
		inital = self.flow.pop()

		# Save the old loop points, and set new ones.
		oldBreak = self.flow.bags.get('break', [])
		self.flow.bags['break'] = [breakF]
		oldContinue = self.flow.bags.get('continue', [])


		# Iterate until convergence

		current = inital.split()
		while 1:
			# TODO undef the index?
			self.flow.bags['continue'] = [current.split()]
			self.flow.restore(current.split())

			body = self(node.body)

			index = self(node.index)
			bodyPreamble = self(node.bodyPreamble)

			# HACK
			#self.flow.undefine(node.index)

			loopEntry = self.flow.pop()
			current, changed = meet(self.meet, current, loopEntry)

			if not changed:
				break


		self.flow.restore(current)

		# Restore the loop points
		self.flow.bags['break'] = oldBreak
		self.flow.bags['continue'] = oldContinue

		# HACK horrible!
		self.strategy.marker(node.iterator)

		iterator = self(node.iterator)
		loopPreamble = self(node.loopPreamble)

		return ast.For(iterator, index, loopPreamble, bodyPreamble, body, else_)

	@dispatch(ast.TryExceptFinally)
	def visitTryExceptFinally(self, node):
		#assert node.finally_ is None, node.finally_

		bags = self.flow.saveBags()
		exitF = self.flow.pop()


		def evalFinallyOn(normal):
			# Restore bags
			self.flow.saveBags()
			for name, bag in bags.iteritems():
				if bag:
					frame, = bag
					self.flow.bags[name] = [frame]

			if normal is not None:
				normal = normal.split()
			self.flow.restore(normal)
			finally_ = self(node.finally_)
			normal = self.flow.pop()
			return normal, finally_

		# Make a "super contour" and evaluate the finally block.
		allF = [exitF]
		for name, bag in bags.iteritems():
			if bag:
				frame, = bag
				allF.append(frame)
		superF, changed = meet(self.meet, *allF)

		superF, finally_ = evalFinallyOn(superF)

		# Evaluate each contour precisely
		exitF, junk = evalFinallyOn(exitF)

		newbags = {}
		for name, bag in bags.iteritems():
			if bag:
				frame, = bag
				newframe, junk = evalFinallyOn(frame)
				newbags[name] = [newframe]


		self.flow.saveBags()
		self.flow.restoreBags(newbags)


		if exitF is not None:
			raiseF = exitF.split()
		else:
			raiseF = None

		raiseEntries = []
		handlers = []
		defaultHandler = None


		else_ = None

		normalF = exitF.split() if exitF is not None else None

		if node.else_ is not None:
			self.flow.restore(normalF)
			else_ = self(node.else_)
			normalF = self.flow.pop()

		for handler in node.handlers:
			if raiseF is not None:
				newF = raiseF.split()
			else:
				newF = None

			self.flow.restore(newF)
			handlers.append(self(handler))
			raiseEntries.append(self.flow.pop())

		if node.defaultHandler is not None:
			self.flow.restore(raiseF)
			defaultHandler = self(node.defaultHandler)
			raiseEntries.append(self.flow.pop())
		else:
			raiseEntries.append(exitF)


		raiseF, changed = meet(self.meet, *raiseEntries)

		self.flow.restore(normalF)

		oldRaise = self.flow.bags.get('raise', [])
		self.flow.bags['raise'] = [raiseF]
		self.flow.tryLevel += 1

		body = self(node.body)

		self.flow.tryLevel -= 1
		self.flow.bags['raise'] = oldRaise

		return ast.TryExceptFinally(body, handlers, defaultHandler, else_, finally_)

	@dispatch(ast.ShortCircutOr)
	def visitShortCircutOr(self, node):
		assert False, node

	@dispatch(ast.ShortCircutAnd)
	def visitShortCircutAnd(self, node):
		assert False, node



	@dispatch(ast.Break)
	def visitBreak(self, node):
		self.flow.restoreDup('break')
		return self.strategy(node)

	@dispatch(ast.Continue)
	def visitContinue(self, node):
		self.flow.restoreDup('continue')
		return self.strategy(node)

	@dispatch(ast.Return)
	def visitReturn(self, node):
		self.flow.restoreDup('return')
		return self.strategy(node)

	@dispatch(ast.Raise)
	def visitRaise(self, node):
		self.flow.restoreDup('raise')
		return self.strategy(node)
