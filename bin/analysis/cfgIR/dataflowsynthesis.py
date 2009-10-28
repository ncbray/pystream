from util.typedispatch import *
from util import xcollections
from analysis.dataflowIR import graph

from . import cfg
from . import dumpcfgir
from . import structuralanalysis


def shouldSchedule(node):
	return isinstance(node, (graph.OpNode))

class CFGResynthesis(object):
	def __init__(self):
		self.predicateCount = xcollections.defaultdict(lambda: 0)
		self.depends = {}
		self.wavefront = set()

		self.blocks = []

	# Collect information about the dataflow graph to guide the next pass.
	def gatherInfo(self, nodes, hyperblock, entryPredicate):
		self.hyperblock = hyperblock
		self.entryPredicate = entryPredicate

		self.wavefront.update(nodes)
		self.scheduled = set()

		self.processed = set()
		self.pending   = set()

		self.pending.update(nodes)

		while self.pending:
			current = self.pending.pop()
			self.processed.add(current)

			if shouldSchedule(current):
				assert all([node is not None for node in current.reverse()]), (current, current.reverse())
				self.depends[current] = frozenset(node.defn for node in current.reverse() if node.isMutable() and (node.hyperblock is hyperblock))
				self.predicateCount[current.canonicalpredicate] += 1

			for next in current.forward():
				if next not in self.processed:
					if next.hyperblock is hyperblock:
						self.pending.add(next)

		return self.schedule()

	# Split the CFG blocks that branch at these predicates.
	def split(self, source):
		newblocks = []

		for block in self.blocks:
			if source.canonicalpredicate and source.canonicalpredicate in block.predicates:
				branch = cfg.CFGBranch(source)
				block.addNext(branch)

				for sibling in source.predicates:
					newkey = block.predicates.union((sibling.canonical(),))
					newblock = cfg.CFGBlock(self.hyperblock, newkey)
					newblocks.append(newblock)
					branch.addNext(newblock)
			else:
				# The split will not occur in this branch.
				newblocks.append(block)

		self.blocks = newblocks
		self.activePredicates.update(source.predicates)

	# Clone the op into every block that has a matching predicate
	def putOpInBlocks(self, op):
		# Computations on predicates should not be present in the CFG
		if op.isPredicateOp(): return

		cp = op.canonicalpredicate
		
		# Entry point and merges have no predicates, so fake it.
		if cp is None:
			# Note this is the entryPredicate for the current hyperblock,
			# not the global entry predicate
			cp = self.entryPredicate.canonical()

		if cp and cp not in self.activePredicates:
			self.split(op.canonicalpredicate.source)

		for block in self.blocks:
			if cp in block.predicates:
				block.ops.append(op)

	# Count the number of times the op will be duplicated
	def countDuplication(self, op):
		# Computations on predicates should not be present in the CFG
		if op.isPredicateOp(): return 0

		count = 0
		for block in self.blocks:
			if op.canonicalpredicate in block.predicates:
				count += 1

	# Mark all the ops that become available after this op is executed.
	def scheduleOp(self, op):
		self.scheduled.add(op)
		self.predicateCount[op.canonicalpredicate] -= 1
		# TODO merge when no more uses of the predicate are left?

		for next in op.forward():
			use = next.use
			if use is None: continue

			assert shouldSchedule(use), (next, use)

			if use.hyperblock is self.hyperblock and use not in self.scheduled:
				if self.scheduled.issuperset(self.depends[use]):
					self.wavefront.add(use)

	# Heuristically choose the next op to schedule.
	def chooseBest(self):
		best = None
		bestcount = 0
		for op in self.wavefront:
			opcount = self.countDuplication(op)

			if best is None or op.canonicalpredicate is None:
				best = op
				bestcount = opcount
			else:
				if op.canonicalpredicate in self.activePredicates:
					if best.canonicalpredicate is not None and best.canonicalpredicate not in self.activePredicates:
						best = op
						bestcount = opcount
					elif best.isBranch() and not op.isBranch():
						best = op
						bestcount = opcount
					elif opcount < bestcount:
						best = op
						bestcount = opcount

		self.wavefront.remove(best)
		return best

	# Place all ops into CFG blocks
	def schedule(self):
		key = frozenset((self.entryPredicate.canonical(),))
		self.entryBlock = cfg.CFGBlock(self.hyperblock, key)
		self.blocks.append(self.entryBlock)
		self.activePredicates = set((self.entryPredicate,))

		while self.wavefront:
			current = self.chooseBest()

			if not isinstance(current, graph.Split):
				self.putOpInBlocks(current)

			self.scheduleOp(current)

		return self.entryBlock, self.blocks


class HyperblockInfo(object):
	def __init__(self, hyperblock):
		self.hyperblock = hyperblock
		self.entryPredicate = None

		self.entry  = None
		self.merges = []
		self.ops    = []
		self.gates  = []
		self.exit   = None

		self.entryEdges = xcollections.defaultdict(set)
		self.exitEdges  = xcollections.defaultdict(set)

	def entryNodes(self):
		if self.entry:
			assert not self.merges
			entry = [self.entry]
		else:
			entry = self.merges
		return entry


# Split the graph into hyperblocks
class HighLevelAnalysis(TypeDispatcher):
	def __init__(self):
		self.entryblock      = None
		self.exitblock       = None
		self.returnPredicate = None

		self.predicateDepends = {}

		self.blockInfo   = xcollections.lazydict(lambda hyperblock: HyperblockInfo(hyperblock))

	@dispatch(graph.Split)
	def vistSplit(self, node):
		info = self.blockInfo[node.hyperblock]
		info.ops.append(node)


	@dispatch(graph.Gate)
	def vistGate(self, node):
		info = self.blockInfo[node.hyperblock]
		info.gates.append(node)

	@dispatch(graph.GenericOp)
	def vistGenericOp(self, node):
		info = self.blockInfo[node.hyperblock]
		info.ops.append(node)

		if node.predicates:
			for p in node.predicates:
				self.predicateDepends[p.canonical()] = node.predicate.canonical()


	@dispatch(graph.Merge)
	def vistMerge(self, node):
		info = self.blockInfo[node.hyperblock]
		info.merges.append(node)

		if node.modify.isPredicate():
			info.entryPredicate = node.modify.canonical()

			for prev in node.reads:
				defn = prev.defn
				canonical = defn.predicate.canonical()

				assert isinstance(defn, graph.Gate), defn
				info.entryEdges[defn.hyperblock].add(canonical)

				prevInfo = self.blockInfo[defn.hyperblock]
				prevInfo.exitEdges[node.hyperblock].add(canonical)



	@dispatch(graph.Entry)
	def vistEntry(self, node):
		info = self.blockInfo[node.hyperblock]
		info.entry = node

		self.entryblock = node.hyperblock
		info.entryPredicate = node.modifies['*']

	@dispatch(graph.Exit)
	def visitExit(self, node):
		info = self.blockInfo[node.hyperblock]
		info.exit = node

		self.exitblock = node.hyperblock
		self.returnPredicate = node.predicate

	def mark(self, node):
		assert isinstance(node, graph.OpNode), node
		if not node in self.processed:
			self.processed.add(node)
			self.queue.append(node)

	# Collect information about each hyperblock
	def collectInfo(self, dataflow):
		self.processed = set()
		self.queue = []

		self.mark(dataflow.entry)

		while self.queue:
			current = self.queue.pop()
			self(current)
			for nextSlot in current.forward():
				for nextOp in nextSlot.forward():
					self.mark(nextOp)

	# Build the CFG for each hyperblock, then link the hyperblocks together.
	def buildCFG(self):
		# Build the CFG for each hyperblock
		for info in self.blockInfo.itervalues():
			cfgr = CFGResynthesis()
			info.entryCFG, info.exitCFGs = cfgr.gatherInfo(info.entryNodes(), info.hyperblock, info.entryPredicate)

		# Link hyperblocks
		for info in self.blockInfo.itervalues():
			entry = info.entryCFG
			for prev, preds in info.entryEdges.iteritems():
				for prevExit in self.blockInfo[prev].exitCFGs:
					if not prevExit.predicates.isdisjoint(preds):
						prevExit.addNext(entry)

		return self.blockInfo[self.entryblock].entryCFG

	def process(self, dataflow):
		self.collectInfo(dataflow)
		return self.buildCFG()


	def dump(self):
		print "ENTRY BLOCK", self.entryblock
		print

		print "EXIT BLOCK", self.exitblock, self.returnPredicate
		print

		print "PRED DEPENDS"
		for pred, parent in self.predicateDepends.iteritems():
			print pred, parent
		print

		print "BLOCK OPS"
		for block, info in self.blockInfo.iteritems():
			print
			print "="*60
			print block
			print info.entryPredicate
			print

			print "\tEXIT EDGES"
			for prev, preds in info.exitEdges.iteritems():
				print '\t', prev
				for pred in preds:
					print '\t\t', pred
			print

			print "\tENTRY EDGES"
			for prev, preds in info.entryEdges.iteritems():
				print '\t', prev
				for pred in preds:
					print '\t\t', pred
			print


			print "MERGES"
			for op in info.merges:
				print '\t', op
			print

			print "OPS"
			for op in info.ops:
				if not isinstance(op, graph.Split):
					print '\t', op
			print

			print "GATES"
			for op in info.gates:
				print '\t', op
			print

# A hackish attempt at reverse-if conversion.
# TODO improve, support loops.
def process(compiler, dataflow, name, dump=False):
	hla = HighLevelAnalysis()
	cfg = hla.process(dataflow)
	cfg = structuralanalysis.processCFG(compiler, cfg)

	if dump: dumpcfgir.process(compiler, cfg, 'summaries\dataflow', name)
	return cfg
