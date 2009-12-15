from util.typedispatch import *

from PADS.DFS import postorder

# HACK
from flowblocks import *

class BlockWrapper(object):
	def __getitem__(self, key):
		return key.getNext()


def standardSuiteFilter(prev, next):
	return next.numEntries() == 1 and next.numExits() <= 1 and not isinstance(next, NormalExit)

def standardFinallyFilter(prev, next):
	return standardSuiteFilter(prev, next) and not isinstance(prev, EndFinally)

class StructuralAnalyzer(TypeDispatcher):
	def process(self, root, trace=False):
		self.trace=trace

		# Visit the blocks in postorder.
		post = list(postorder(BlockWrapper(), root))

		for block in post:
			self(block)

			if block.isRegion():
				self.process(block.entry())

	@dispatch(EndFinally)
	def visitEndFinally(self, block):
		if isinstance(block.next, Merge) and block.next.numEntries() == 2:
			merge = block.next
			incoming = tuple(merge.incomingSet().difference((block,)))
			assert len(incoming) == 1
			region = incoming[0]
			if isinstance(region, ExceptRegion):
				# This is a EndFinally from an exception handling region,
				# further more it links to an else block.
				# If the EndFinally is paired with an exception handling region, it will NEVER exit normally.
				# (It will reraise the exception.)
				# The spurious exit complicates the flow graph when there is an else, so cut the link.
				block.next.replacePrev(block, None)
				block.replaceNext(merge, None)

	@dispatch(Return, Break, Continue, Raise, NormalExit, Linear)
	def visitLeaf(self, block):
		pass

	@dispatch(Merge)
	def visitMerge(self, block):
		# TODO eliminate null merges?  (hard, as the length of the incoming set may be less than the number of edges.)

		if block.numEntries() == 1:
			block.eliminate()
		elif block.loopMerge or (block.numEntries() == 2 and len(block.incomingSet()) == 2):
			if isinstance(block.next, ForIter):
				# Loop comprehensions will not be marked as "loop merge"

				body = block.next.iter
				assert body.isSESE()

				assert body.next == block, (body.next, block)

				entry = block.findLoopEntry(body)

				entryEdge = CFGEdge(entry, block)
				exitEdge = CFGEdge(block.next, block.next.done)

				region = ForLoop(block.region, block.next.origin, block.next.iter)
				self.moveIntoRegion(entryEdge, exitEdge, region)
				return

			elif isinstance(block.next, Linear):
				switch = block.next.next
				if isinstance(switch, Switch):
					body = switch.t
					if body.isSESE() and body.next == block:
						assert block.loopMerge

						entry = block.findLoopEntry(body)

						cond = switch.cond.replaceDefault(block.next)
						region = WhileLoop(block.region, cond.origin, cond, block.next, switch.t)

						entryEdge = CFGEdge(entry, block)
						exitEdge = CFGEdge(switch, switch.f)
						self.moveIntoRegion(entryEdge, exitEdge, region)
						return

			incoming = tuple(block.incomingSet())
			if isinstance(incoming[0], NormalEntry) or isinstance(incoming[1], NormalEntry):
				# This is an infinite "while" loop with the condition folded away.

				if isinstance(incoming[0], NormalEntry):
					entry = incoming[0]
				else:
					entry = incoming[1]


				self.contractSuite(block, block.next)

				# TODO origin?
				region = WhileLoop(block.region, None, None, None, block.next)

				entryEdge = CFGEdge(entry, block)
				self.moveIntoRegion(entryEdge, None, region)
				return

		assert not isinstance(block.next, ForIter), (block.numEntries(), len(block.incoming), block.incomingCount.values(), block.incoming)


	def makeSuite(self, entryEdge, exitEdge):
		assert isinstance(entryEdge, CFGEdge)
		assert isinstance(exitEdge, CFGEdge)

		if entryEdge != exitEdge:
			assert not entryEdge.source == exitEdge.source, (entryEdge, exitEdge)
			start 	= entryEdge.destination
			end 	= exitEdge.source

			if start != end:
				region = SuiteRegion(entryEdge.destination.region, start.origin)
				self.moveIntoRegion(entryEdge, exitEdge, region)

				# HACK
				entryEdge.desination = region
				exitEdge.source = region

	def shortenSwitchExits(self, block):
		assert block.t.isSESE() or isinstance(block.t, Merge), block.t
		assert block.f.isSESE() or isinstance(block.f, Merge), block.f
		assert block.t != block.f

		self.contractSuite(block, block.t)
		self.contractSuite(block, block.f)

	def contractSuite(self, src, dst, edgeFilter=standardSuiteFilter):
		sentry = CFGEdge(src, dst)
		sexit = self.findLinearExit(sentry, edgeFilter)
		self.makeSuite(sentry, sexit)

	def subCond(self, cond, newblock):
		if cond == None:
			return newblock
		elif isinstance(cond, tuple):
			return (cond[0], self.subCond(cond[1], newblock), self.subCond(cond[2], newblock))
		else:
			return cond

	def findSwitchExitEdge(self, texit, fexit):
		if texit.destination and fexit.destination:
			assert texit.destination == fexit.destination
			assert isinstance(texit.destination, Merge), repr(texit.destination)
			merge = texit.destination
			exitEdge = merge.pulloutMerge(texit.source, fexit.source)
		elif texit.destination and not fexit.destination:
			exitEdge = texit
		elif not texit.destination and fexit.destination:
			exitEdge = fexit
		elif not texit.destination and not fexit.destination:
			exitEdge = None

		return exitEdge

	def spliceContinue(self, block):
		assert block.numExits() == 1 and isinstance(block.next, Merge), block
		#assert block.next.loopMerge, block

		c = Continue(block.region, block.origin)

		merge = block.next

		merge.replacePrev(block, None)
		c.replacePrev(None, block)
		block.replaceNext(merge, c)


	def spliceContinueContract(self, parent, block):
		self.spliceContinue(block)
		self.contractSuite(parent, block)

	@dispatch(Switch)
	def visitSwitch(self, block):
		self.shortenSwitchExits(block)

		assert block.t.isSESE() or isinstance(block.t, Merge), block.t
		assert block.f.isSESE() or isinstance(block.f, Merge), block.f

		tentry = CFGEdge(block, block.t)
		texit = self.findLinearExit(tentry, standardSuiteFilter)

		fentry = CFGEdge(block, block.f)
		fexit = self.findLinearExit(fentry, standardSuiteFilter)

		entryEdge = CFGEdge(block.prev, block)

		if texit.destination and fexit.destination:
			if texit.destination != fexit.destination:
				if isinstance(texit.destination, Merge) and isinstance(fexit.destination, NormalExit):
					# A while loop?
					assert isinstance(block.region, LoopRegion)
					return

				if isinstance(block.t, Merge) and isinstance(block.f, Linear):
					nextSwitch = block.f.getNext()[0]
					if isinstance(nextSwitch, Switch) and nextSwitch.t == block.t:
						# Short circut OR

						assert block.t.isShortCircutMerge()

						cond = block.f
						entryEdge = CFGEdge(block.prev, block)
						exitT = block.t.pulloutMerge(block, nextSwitch)
						exitF = CFGEdge(nextSwitch, nextSwitch.f)

						block.cond = ShortCircutOr(block.region, block.origin, block.cond, nextSwitch.cond.replaceDefault(cond))

						# Cut out the or graph.
						block.replaceNext(block.t, exitT.destination)
						exitT.destination.replacePrev(exitT.source, block)

						block.replaceNext(block.f, exitF.destination)
						exitF.destination.replacePrev(exitF.source, block)

						self.visitSwitch(block) # Try again.
						return

				elif isinstance(block.f, Merge) and isinstance(block.t, Linear):
					nextSwitch = block.t.getNext()[0]
					if isinstance(nextSwitch, Switch) and nextSwitch.f == block.f:
						# Short circut AND

						assert block.f.isShortCircutMerge()

						cond = block.t
						entryEdge = CFGEdge(block.prev, block)
						exitF = block.f.pulloutMerge(block, nextSwitch)
						exitT = CFGEdge(nextSwitch, nextSwitch.t)

						block.cond = ShortCircutAnd(block.region, block.origin, block.cond, nextSwitch.cond.replaceDefault(cond))


						# Cut out the or graph.
						block.replaceNext(block.t, exitT.destination)
						exitT.destination.replacePrev(exitT.source, block)

						block.replaceNext(block.f, exitF.destination)
						exitF.destination.replacePrev(exitF.source, block)

						self.visitSwitch(block) # Try again.
						return

				# We can't figure out what to do with this switch?
				def shouldSplice(primary, alt):
					# Don't splice if this is will be a short circut merge...
					if alt.destination:
						if not isinstance(alt.destination, Merge) or not alt.destination.isShortCircutMerge():
							if isinstance(primary.destination, Merge) and primary.destination.loopMerge:
								return True
					return False

				if block.isShortCircut():
					return

				if shouldSplice(texit, fexit):
					self.spliceContinueContract(block, block.t)

				elif shouldSplice(fexit, texit):
					self.spliceContinueContract(block, block.f)
				else:
					return


		if self.isWhileLoopHeader(block.prev):
			return

		# Don't turn a potential short circut into a switch.
		if isinstance(block.t, Merge) and block.t.isShortCircutMerge():
			return

		if isinstance(block.f, Merge) and block.f.isShortCircutMerge():
			return


		tentry = CFGEdge(block, block.t)
		texit = self.findLinearExit(tentry, standardSuiteFilter)

		fentry = CFGEdge(block, block.f)
		fexit = self.findLinearExit(fentry, standardSuiteFilter)


		if texit.destination and fexit.destination:
			assert texit.destination == fexit.destination
			assert isinstance(texit.destination, Merge), repr(texit.destination)
			exitEdge = texit.destination.pulloutMerge(texit.source, fexit.source)
		elif texit.destination and not fexit.destination:
			exitEdge = texit
		elif not texit.destination and fexit.destination:
			exitEdge = fexit
		elif not texit.destination and not fexit.destination:
			exitEdge = None

		t = None if isinstance(block.t, Merge) else block.t
		f = None if isinstance(block.f, Merge) else block.f

		region = SwitchRegion(block.region, block.origin, block.cond, t, f)

		self.moveIntoRegion(entryEdge, exitEdge, region)


	def isWhileLoopHeader(self, block):
		if isinstance(block.region, LoopRegion):
			if hasattr(block, 'prev') and isinstance(block.prev, NormalEntry) and isinstance(block, Linear) and isinstance(block.next, Switch):
				switch = block.next

				assert not(isinstance(switch.f, Merge) and switch.f.numEntries() == 1)

				exitstart = switch.f

				if isinstance(exitstart, Linear) and isinstance(exitstart.next, NormalExit) and not exitstart.containsOperations():
					# This is a while loop header.
					return True
		return False


	@dispatch(ForIter)
	def visitForIter(self, block):
		self.contractSuite(block, block.iter)

	@dispatch(NormalEntry)
	def visitNormalEntry(self, block):
		if isinstance(block.region, LoopRegion):
			# This is the start of a loop with no exit.

			assert block.next

			# Should have alread been taken care of.
			assert not isinstance(block.next, Merge)
			assert not (isinstance(block.next, Linear) and isinstance(block.next.next, Merge))
			# At this point we know this is not a loop that can iterate more than once.

			if self.isWhileLoopHeader(block.next):
				# Degenerate while loop
				entry = block
				linear = block.next
				switch = linear.next
				cond = switch.cond.replaceDefault(linear)

				region = WhileLoop(block.region, cond.origin, cond, linear, switch.t)

				entryEdge = CFGEdge(entry, linear)
				exitEdge = CFGEdge(switch, switch.f)

				self.moveIntoRegion(entryEdge, exitEdge, region)

			elif isinstance(block.next, Linear) and isinstance(block.next.next, ForIter):
				# Degenerate for loop
				linear = block.next
				it = linear.next

				entryEdge = CFGEdge(linear, it)
				exitEdge = CFGEdge(it, it.done)

				region = ForLoop(block.region, block.next.origin, it.iter)
				self.moveIntoRegion(entryEdge, exitEdge, region)
			elif isinstance(block.next, Linear) and isinstance(block.next.next, ForLoop):
				pass # Already handled
			elif isinstance(block.next, WhileLoop):
				pass # Alread handled
			else:
				switch = block.next.next
				#assert False, ("Crazy", block.next, switch, switch.f, switch.f.next)
				# This loop region does not exit normally, nor does it have a while loop header or a for loop header.
				# Although this seems crazy, this case is found in Lib/sre_parse.py
				self.contractSuite(block, block.next)

				# TODO origin?
				region = WhileLoop(block.region, None, None, None, block.next)

				entryEdge = CFGEdge(block, block.next)
				self.moveIntoRegion(entryEdge, None, region)

# This doesn't work as expected, as it may cause spurious "else" statements to be attached to nestled loops.

##	def unwindLoopMerge(self, merge, entry):
##		incoming = tuple(merge.incomingSet())
##		for cont in incoming:
##			if cont != entry:
##				self.spliceContinue(cont)
##
##		if merge.numEntries() == 1:
##			merge.eliminate()

	@dispatch(LoopRegion)
	def visitLoopRegion(self, block):
		entry = block.entry().next

		if isinstance(entry, Merge):
			# While loop
##			if isinstance(merge.next, Linear) and isinstance(merge.next.next, Switch):
##				# condition has not been const-folded.

			merge = entry
			entry = block.entry()

			merge.setLoopEntry(entry)
			#self.unwindLoopMerge(merge, entry)


		elif isinstance(entry, Linear) and isinstance(entry.next, Merge):
			# Normal for loop
			merge = entry.next

			merge.setLoopEntry(entry)
			#self.unwindLoopMerge(merge, entry)

		elif isinstance(entry, Linear) and isinstance(entry.next, Switch):
			# Degenerate while loop
			pass
		elif isinstance(entry, Linear) and isinstance(entry.next, ForIter):
			# Degenerate for loop
			pass
		else:
			block.mark()
			entry.mark()
			assert False, "Cannot classify loop."




		if block.normal:
			if block.normal == block.exceptional:
				# No "else"
				assert isinstance(block.exceptional, Merge), "Loop exit is not a merge point?"
				exitEdge = block.normal.pulloutMerge(block, block)
			else:
				# Make a suite for the "else"
				entryEdge = CFGEdge(block, block.normal)
				exitEdge = self.findLinearExit(entryEdge, standardSuiteFilter)

				# If the normal and exceptional control flow does not remerge, but we're inside a loop
				# stick a continue inside the else.
				dest = exitEdge.destination
				if isinstance(dest, Merge) and dest.loopMerge and dest != block.exceptional:
					cont = self.spliceContinue(exitEdge.source)
					exitEdge = CFGEdge(cont, None)

				self.makeSuite(entryEdge, exitEdge)

				if block.normal.isSESE() and block.normal.next != None:

					if block.normal.next != block.exceptional:
						block.mark()
						block.normal.next.mark()

					assert block.normal.next == block.exceptional, ("Loop does not merge?", block.normal, block.normal.next, block.exceptional)
					assert isinstance(block.normal.next, Merge)
					exitEdge = block.exceptional.pulloutMerge(block.normal, block)
				else:
					# Else does not terminate normally.
					#self.contractSuite(block, block.exceptional)
					exitEdge = CFGEdge(block, block.exceptional)
		else:
			# No normal exit.
			exitEdge = CFGEdge(block, block.exceptional)


		assert block.exceptional

		region = LoopElse(block.region, block.origin)
		entryEdge = CFGEdge(block.prev, block)
		self.moveIntoRegion(entryEdge, exitEdge, region)

		assert block.exceptional, exitEdge

	@dispatch(FinallyRegion)
	def visitFinallyRegion(self, block):
		# If normal exit exists, chop at linear terminal after merge.
		# else, chop at linear terminal from finally.

		if block.normal:
			assert isinstance(block.exceptional, Merge), "Finally exit is not a merge point?"
			assert block.exceptional.numEntries() == 2
			self.contractSuite(block.exceptional, block.exceptional.next, standardFinallyFilter)
			exitEdge = CFGEdge(block.exceptional, block.exceptional.next)
		else:
			self.contractSuite(block, block.exceptional, standardFinallyFilter)
			exitEdge = CFGEdge(block, block.exceptional)

		# Step past the contracted suite.
		exitEdge = CFGEdge(exitEdge.destination, exitEdge.destination.next)

		region = TryFinally(block.region, block.origin)

		entryEdge = CFGEdge(block.prev, block)
		self.moveIntoRegion(entryEdge, exitEdge, region)


	def makeExceptionalSuite(self, block):
		assert isinstance(block.exceptional, Linear)

		entryEdge = CFGEdge(block, block.exceptional)

		if isinstance(block.exceptional.next, SwitchRegion):
			# Tests
			exitEdge = CFGEdge(block.exceptional.next, block.exceptional.next.next)
		else:
			# No tests, single except.
			exitEdge = self.findLinearExit(entryEdge, standardSuiteFilter)
			#exitEdge = CFGEdge(block.exceptional, block.exceptional.next)

		self.makeSuite(entryEdge, exitEdge)

	@dispatch(ExceptRegion)
	def visitExceptRegion(self, block):
		# chop except after linear + split*
		# if normal exit exists, chop point must be mutal merge.

		# TODO should the exception branch always be contracted?

		entryEdge = CFGEdge(block, block.exceptional)

		tryBlock = block

		if block.normal:
			self.contractSuite(block, block.normal)

			self.makeExceptionalSuite(block)
##
##			# Make a suite of the exceptions.
##			exitEdge = self.findLinearExit(entryEdge, standardSuiteFilter)
##
##			self.makeSuite(entryEdge, exitEdge)

			if block.normal.isSESE():
				a = CFGEdge(block.normal, block.normal.next)
				elseBlock = block.normal
			else:
				a = CFGEdge(block, block.normal)
				elseBlock = None

			if block.exceptional.isSESE():
				b = CFGEdge(block.exceptional, block.exceptional.next)
				exceptBlock = block.exceptional
			else:
				assert False
				b = CFGEdge(block, block.exceptional)
				exceptBlock = None

			exitEdge = self.findSwitchExitEdge(a, b)
		else:
			self.makeExceptionalSuite(block)
			exitEdge = CFGEdge(block.exceptional, block.exceptional.next)

			elseBlock = None
			exceptBlock = block.exceptional

			# The except block may exit normally, even if the try block does not.

		region = TryExcept(block.region, block.origin)

		region.tryBlock 	= tryBlock
		region.exceptBlock 	= exceptBlock
		region.elseBlock 	= elseBlock

		entryEdge = CFGEdge(block.prev, block)
		self.moveIntoRegion(entryEdge, exitEdge, region)

	@dispatch(CodeBlock)
	def visitCodeBlock(self, block):
		assert False, "Cannot deal with code blocks."
		pass


	def moveIntoRegion(self, entryEdge, exitEdge, region):
		assert isinstance(entryEdge, CFGEdge)
		assert exitEdge == None or isinstance(exitEdge, CFGEdge)

		assert entryEdge.destination.isPrevious(entryEdge.source), entryEdge
		entryOutside = entryEdge.source
		entryInside = entryEdge.destination

		if exitEdge:
			assert not exitEdge.destination or exitEdge.destination.isPrevious(exitEdge.source)
			exitInside = exitEdge.source
			exitOutside = exitEdge.destination

		assert entryEdge.destination

		entrySentinal = NormalEntry(entryInside.region)

		region.replacePrev(None, entryOutside)
		entryOutside.replaceNext(entryInside, region)
		entryInside.replacePrev(entryOutside, entrySentinal)


		assert region.isPrevious(entryOutside), (region, entryOutside)


		# Unlink the exit.
		if exitEdge and exitOutside:
			exitSentinal = NormalExit(exitInside.region)

			region.replaceNext(None, exitOutside)
			exitOutside.replacePrev(exitInside, region)
			exitInside.replaceNext(exitOutside, exitSentinal)

		self.updateRegion(entryInside, entryInside.region, region)

		assert region.prev

		# Hook inside up to the region
		# Done in a distinct step to prevent region conflicts.
		entryInside.replacePrev(entrySentinal, region.entry())
		region.entry().replaceNext(None, entryInside)

		if exitEdge and exitOutside:
			assert region.next
			exitInside.replaceNext(exitSentinal, region.exit()) # Potentially bad.
			region.exit().replacePrev(None, exitInside)

		assert region.isPrevious(entryOutside), (region, entryOutside)

	def findLinearExit(self, edge, f):
		block = edge.source
		next = edge.destination

		while next and f(block, next):
			block = next
			nexts = block.getNext()

			if len(nexts):
				assert len(nexts) == 1
				next = nexts[0]
			else:
				next = None

		return CFGEdge(block, next)


	def updateRegion(self, block, oldregion, newregion):
		assert oldregion != newregion

		if block.region != newregion:
			assert block.region == oldregion
			block.setRegion(newregion)
			for next in block.getNext():
				if next: self.updateRegion(next, oldregion, newregion)
