from base import *

from programIR.python.fold import existingConstant

class ForwardFlowTraverse(object):
	__metaclass__ = typedispatcher

	def __init__(self, adb, meetF, analyze, rewrite):
		self.adb = adb
		self.analyze = analyze
		self.rewrite = rewrite
		self.flow = FlowDict()
		self.tryLevel = 0

		self.mayRaise = MayRaise()

		self.meetF = meetF

	@defaultdispatch
	def default(self, node):
		assert False, repr(node)
		return self.processExpr(node)

	def processExpr(self, node):
		node = self.rewrite(node)

		# Assuming exception handing only cares about locals, save the state before the assign.
		# TODO make sound for heap modificaions/interprocedural?
		if self.flow.tryLevel > 0 and self.mayRaise(node):
			normal, exceptional = self.flow.popSplit()
			self.flow.restore(exceptional)
			self.flow.save('raise')
			self.flow.restore(normal)

		self.analyze(node)
		return node

	# HACK to verify types.
	@dispatch(ast.Assign, ast.Discard,
		  #ast.ConvertToBool,
		  ast.Local, ast.Cell,
		  ast.UnpackSequence, ast.SetAttr, ast.Store,
		  ast.Print, ast.SetSubscript, ast.Delete, ast.SetSlice, ast.DeleteAttr,
		  ast.SetGlobal, ast.DeleteGlobal, ast.DeleteSlice, ast.DeleteSubscript,
		  ast.SetCellDeref)
	def visitOK(self, node):
		return self.processExpr(node)

	@dispatch(list, tuple, ast.ExceptionHandler, type(None))
	def visitFlow(self, node):
		node = xform.allChildren(self, node)
		return node

	@dispatch(ast.Suite)
	def visitFlow(self, node):
		newblocks = []
		for block in node.blocks:
			newblocks.append(self(block))
			if not self.flow._current:
				# Folding control structures can kill subsequent blocks.
				break

		if newblocks != node.blocks:
			return ast.Suite(newblocks)
		else:
			return node

	@dispatch(ast.Condition)
	def visitCondition(self, node):
		return ast.Condition(self(node.preamble), self.processExpr(node.conditional))

	@dispatch(ast.Switch)
	def visitSwitch(self, node):
		condition = self(node.condition)

		# Can the switch be constant folded?
		# Done inside dataflow analysis, as it can
		# greatly improve precision

		cond = condition.conditional
		if existingConstant(cond):
			value = cond.object.pyobj
			taken = node.t if value else node.f
			# Note: condtion.conditional is killed, as
			# it is assumed to be a reference.
			return ast.Suite([condition.preamble, self(taken)])


		# Split
		tf, ff = self.flow.popSplit()

		self.flow.restore(tf)
		t = self(node.t)
		tf = self.flow.pop()

		self.flow.restore(ff)
		f = self(node.f)
		ff = self.flow.pop()

		# Merge
		merged, changed = meet(self.meetF, tf, ff)
		self.flow.restore(merged)

		result = ast.Switch(condition, t, f)

		return result


	@dispatch(ast.While)
	def visitWhile(self, node):
		condition = self(node.condition)

		originalbags = self.flow.saveBags()
		current = self.flow.pop()

		# Iterate until convergence
		while 1:
			self.flow.restore(current.split())

			body = self(node.body)

			# Construct the state at loop exit
			self.flow.save('continue')
			self.flow.mergeCurrent(self.meetF, 'continue')

			if self.flow._current:
				condition = self(node.condition)
				loopExit = self.flow.pop()

				# Has a fixed point been reached for loop exit?
				# Check merge(current, "normal exit") == current
				# HACK does not iterate

				current, changed = meet(self.meetF, current, loopExit)
				shouldTerminate = not changed
			else:
				# Degenerate loop.
				# Leave current alone, as the loop may not be taken.
				shouldTerminate = True

			if shouldTerminate:
				# Construct the state at loop break
				self.flow.mergeCurrent(self.meetF, 'break')
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
		if out:
			self.flow.restore(out)
			else_ = self(node.else_)
			out = self.flow.pop()
		else:
			# Else never taken.
			else_ = ast.Suite([])


		# Merge in breaks
		out, changed = meet(self.meetF, out, b)
		self.flow.restore(out)

		result = ast.While(condition, body, else_)

		return result

	@dispatch(ast.For)
	def visitFor(self, node):
		loopPreamble = self(node.loopPreamble)
		iterator = self(node.iterator)
		#index = self(node.index)

		originalbags = self.flow.saveBags()
		current = self.flow.pop()

		# Iterate until convergence
		while 1:
			self.flow.restore(current.split())

			# TODO Need to invalidate index every iteration.
			# Really, we're evaluating index = next(iterator)

			# HACK
			#self.flow.undefine(node.index)
			#index = node.index

			bodyPreamble = self(node.bodyPreamble)
			index = self(node.index)

			body = self(node.body)

			# Construct the state at loop exit
			self.flow.save('continue')
			self.flow.mergeCurrent(self.meetF, 'continue')
			c = self.flow.pop()

			# Has a fixed point been reached for loop exit?
			# Check merge(current, "normal exit") == current
			# HACK does not iterate

			current, changed = meet(self.meetF, current, c)

			if not changed:
				# Construct the state at loop break
				self.flow.mergeCurrent(self.meetF, 'break')
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
		else_ = self(node.else_)

		# Merge in breaks
		out = self.flow.pop()
		out, changed = meet(self.meetF, out, b)
		self.flow.restore(out)

		result = ast.For(iterator, index, loopPreamble, bodyPreamble, body, else_)
		return result

	@dispatch(ast.TryExceptFinally)
	def visitTryExceptFinally(self, node):
		oldRaise = self.flow.bags.get('raise', [])
		self.flow.bags['raise'] = []

		self.flow.tryLevel += 1
		body = self(node.body)
		self.flow.tryLevel -= 1

		normalF = self.flow.pop()


		self.flow.mergeCurrent(self.meetF, 'raise')
		raiseF = self.flow.pop()


		self.flow.bags['raise'] = oldRaise

		normalExits = []
		handlers = []
		defaultHandler = None

		if raiseF is not None:
			for handler in node.handlers:
				self.flow.restore(raiseF.split())
				handlers.append(self(handler))
				normalExits.append(self.flow.pop())

			if node.defaultHandler is not None:
				self.flow.restore(raiseF)
				defaultHandler = self(node.defaultHandler)
				normalExits.append(self.flow.pop())
			else:
				# No default handler, raises my propigate.
				self.flow.restore(raiseF)
				self.flow.save('raise')

		if node.else_ is not None and normalF is not None:
			self.flow.restore(normalF)
			else_ = self(node.else_)
			normalExits.append(self.flow.pop())
		else:
			else_ = None
			normalExits.append(normalF)


		normalF, changed = meet(self.meetF, *normalExits)

		originalbags = self.flow.saveBags()
		mergedbags = {}
		allF = [normalF]



		for name, bag in originalbags.iteritems():
			if bag:
				merged, changed = meet(self.meetF, *bag)

				if merged is not None:
					mergedbags[name] = merged
					allF.append(merged)

		# Generate the code by evaluating the superposition

		superF, changed = meet(self.meetF, *allF)
		self.flow.restore(superF)
		finally_ = self(node.finally_)

		# Clear the analysis state
		self.flow.pop()
		self.flow.saveBags()


		# Evaluate each contour seperately to maintain precision.
		if normalF is not None:
			self.flow.restore(normalF)
			self(node.finally_)
			normalF = self.flow.pop()

		for name, frame in mergedbags.iteritems():
			frame = frame.split() if frame is not None else None
			self.flow.restore(frame)
			self(node.finally_)
			self.flow.save(name)

		self.flow.restore(normalF)

		result = ast.TryExceptFinally(body, handlers, defaultHandler, else_, finally_)

		return result

	@dispatch(ast.ShortCircutOr)
	def visitShortCircutOr(self, node):
		assert False, node

	@dispatch(ast.ShortCircutAnd)
	def visitShortCircutAnd(self, node):
		assert False, node

	@dispatch(ast.Break)
	def visitBreak(self, node):
		result = self.processExpr(node)
		self.flow.save('break')
		return result

	@dispatch(ast.Continue)
	def visitContinue(self, node):
		result = self.processExpr(node)
		self.flow.save('continue')
		return result

	@dispatch(ast.Return)
	def visitReturn(self, node):
		result = self.processExpr(node)
		self.flow.save('return')
		return result

	@dispatch(ast.Raise)
	def visitRaise(self, node):
		result = self.processExpr(node)
		self.flow.save('raise')
		return result



#	@dispatch(ast.Code)
#	def visitCode(self, node):
#		node = ast.Code(
#			node.name,
#			node.selfparam,
#			node.parameters,
#			node.parameternames,
#			node.vparam,
#			node.kparam,
#			node.returnparam,
#			self(node.ast)
#			)

#		return node
