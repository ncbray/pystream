from base import *

def constMeet(values):
	prototype = values[0]
	for value in values[1:]:
		if value != prototype:
			return top
	return prototype


# Parameterize
#	Preflow
#	Postflow
# 	Statement
	
class ForwardFlowTraverse(object):
	__metaclass__ = typedispatcher
	
	def __init__(self, strategy):
		self.strategy = strategy
		self.flow = FlowDict()
		self.tryLevel = 0

	@defaultdispatch
	def default(self, node):
		#assert False, node
		
		print self.tryLevel, node
		if self.tryLevel > 0 and isinstance(node, ast.SimpleStatement):
			normal, exceptional = self.flow.popSplit()
			self.flow.restore(exceptional)
			self.flow.save('raise')
			self.flow.restore(normal)

			print "Raise?", node
			
		node = xform.allChildren(self.strategy, node)
		return node

	@dispatch(ast.Switch)
	def visitSwitch(self, node):
		condition = self.strategy(node.condition)

		# Split
		tf, ff = self.flow.popSplit()

		self.flow.restore(tf)
		t = self.strategy(node.t)
		tf = self.flow.pop()

		self.flow.restore(ff)
		f = self.strategy(node.f)
		ff = self.flow.pop()

		# Merge
		merged, changed = meet(constMeet, tf, ff)
		self.flow.restore(merged)

		return ast.Switch(condition, t, f)


	@dispatch(ast.While)
	def visitWhile(self, node):
		condition = self.strategy(node.condition)

		originalbags = self.flow.saveBags()
		current = self.flow.pop()

		# Iterate until convergence
		while 1:			
			self.flow.restore(current.split())
			
			body = self.strategy(node.body)
			condition = self.strategy(node.condition)

			# Construct the state at loop exit
			self.flow.save('continue')
			self.flow.mergeCurrent(constMeet, 'continue')
			loopExit = self.flow.pop()

			# Has a fixed point been reached for loop exit?
			# Check merge(current, "normal exit") == current
			# HACK does not iterate

			current, changed = meet(constMeet, current, loopExit)

			if not changed:
				# Construct the state at loop break
				self.flow.mergeCurrent(constMeet, 'break')
				b = self.flow.pop()

				# Save the exceptional flow
				loopbags = self.flow.saveBags()
				assert 'continue' not in loopbags
				assert 'break' not in loopbags

				break
			else:
				# Clears the bags
				self.flow.saveBags()

		# Merge in newly create bages (raise, return, etc.)
		self.flow.restoreAndMergeBags(originalbags, loopbags)

		# TODO If loop must be taken, do not merge in current.
		# Use "c" instead.
		out = current

		# Evaluate else.
		self.flow.restore(out)
		else_ = self.strategy(node.else_)
		
		# Merge in breaks
		out = self.flow.pop()
		out, changed = meet(constMeet, out, b)
		self.flow.restore(out)

		return ast.While(condition, body, else_)

	@dispatch(ast.For)
	def visitFor(self, node):
		iterator = self.strategy(node.iterator)
		#index = self.strategy(node.index)

		originalbags = self.flow.saveBags()
		current = self.flow.pop()

		# Iterate until convergence
		while 1:			
			self.flow.restore(current.split())

			# TODO Need to invalidate index every iteration.
			# Really, we're evaluating index = next(iterator)

			# HACK
			self.flow.current.undefine(node.index)
			index = node.index
			
			body = self.strategy(node.body)

			# Construct the state at loop exit
			self.flow.save('continue')
			self.flow.mergeCurrent(constMeet, 'continue')
			c = self.flow.pop()

			# Has a fixed point been reached for loop exit?
			# Check merge(current, "normal exit") == current
			# HACK does not iterate

			current, changed = meet(constMeet, current, c)

			if not changed:
				# Construct the state at loop break
				self.flow.mergeCurrent(constMeet, 'break')
				b = self.flow.pop()

				# Save the exceptional flow
				loopbags = self.flow.saveBags()
				assert 'continue' not in loopbags
				assert 'break' not in loopbags

				break
			else:
				# Clears the bags
				self.flow.saveBags()

		# Merge in newly create bages (raise, return, etc.)
		self.flow.restoreAndMergeBags(originalbags, loopbags)

		# TODO If loop must be taken, do not merge in current.
		# Use "c" instead.
		out = current

		# Evaluate else.
		self.flow.restore(out)
		else_ = self.strategy(node.else_)
		
		# Merge in breaks
		out = self.flow.pop()
		out, changed = meet(constMeet, out, b)
		self.flow.restore(out)

		return ast.For(iterator, index, body, else_)

	@dispatch(ast.TryExceptFinally)
	def visitTryExceptFinally(self, node):
		oldBags = self.flow.saveBags()

		self.tryLevel += 1
		body = self.strategy(node.body)
		self.tryLevel -= 1
		
		assert False
		

	@dispatch(ast.ShortCircutOr)
	def visitShortCircutOr(self, node):
		assert False, node

	@dispatch(ast.ShortCircutAnd)
	def visitShortCircutAnd(self, node):
		assert False, node

	@dispatch(ast.Break)
	def visitBreak(self, node):
		self.flow.save('break')
		return node

	@dispatch(ast.Continue)
	def visitContinue(self, node):
		self.flow.save('continue')
		return node

	@dispatch(ast.Return)
	def visitReturn(self, node):
		result = xform.allChildren(self.strategy, node)
		self.flow.save('return')
		return result

	@dispatch(ast.Raise)
	def visitRaise(self, node):
		result = xform.allChildren(self.strategy, node)		
		self.flow.save('raise')
		return result
