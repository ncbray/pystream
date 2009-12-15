from util.typedispatch import *
from language.python import ast

import pydot
from util.io import filesystem
from util.asttools import astpprint

import analysis.dataflowIR.graph as graph

from util.application.async import *

class NodeStyle(TypeDispatcher):
	localColor     = 'lime'
	localLineColor = 'darkgreen'

	existingColor  = 'orange'
	existingLineColor  = 'orange'

	nullColor = 'gray'

	heapColor = 'aliceblue'
	heapLineColor = 'blue'

	opColor = 'lightyellow'

	splitColor = 'cyan'
	mergeColor = 'magenta'
	gateColor  = 'purple'

	predicateColor = 'red'
	predicateLineColor = 'darkred'

	compoundColor = 'cyan'
	compoundLineColor = 'black'

	@dispatch(graph.Entry, graph.Exit)
	def handleTerminal(self, node):
		return dict(shape='point', fontsize=8)

	@dispatch(graph.FieldNode)
	def handleFieldNode(self, node):
		label = "%r\\n%r" % (node.name.object, node.name.slotName)
		return dict(label=label, shape='box', style='filled', fillcolor=self.heapColor, fontsize=8)

	@dispatch(graph.LocalNode)
	def handleLocalNode(self, node):
		label = "\\n".join(repr(name) for name in node.names)
		return dict(label=label, shape='box', style='filled', fillcolor=self.localColor, fontsize=8)

	@dispatch(graph.PredicateNode)
	def handlePredicateNode(self, node):
		label = str(node.name)
		return dict(label=label, shape='box', style='filled', fillcolor=self.predicateColor, fontsize=8)


	@dispatch(graph.ExistingNode)
	def handleExistingNode(self, node):
		label = str(node.name)
		return dict(label=label, shape='box', style='filled', fillcolor=self.existingColor, fontsize=8)

	@dispatch(graph.NullNode)
	def handleNullNode(self, node):
		label = "NULL"
		return dict(label=label, shape='box', style='filled', fillcolor=self.nullColor, fontsize=8)

	@dispatch(graph.GenericOp)
	def handleGenericOp(self, node):
		op = node.op
		if isinstance(op, ast.TypeSwitch):
			label = op.__class__.__name__
		else:
			label = astpprint.toString(op, eol='\\n')

		return dict(label=label, shape='box', style='filled', fillcolor=self.opColor, fontsize=8)

	@dispatch(graph.Split)
	def handleSplit(self, node):
		return dict(label='split', style='filled', fillcolor=self.splitColor, fontsize=8)

	@dispatch(graph.Gate)
	def handleGate(self, node):
		return dict(label='gate', shape='invtriangle', style='filled', fillcolor=self.gateColor, fontsize=8)


	@dispatch(graph.Merge)
	def handleMerge(self, node):
		return dict(label='merge', shape='triangle', style='filled', fillcolor=self.mergeColor, fontsize=8)


class DataflowToDot(TypeDispatcher):
	def __init__(self, g, cluster):
		self.g = g
		self.cluster = cluster
		self.nodes     = {}
		self.processed = set()
		self.queue     = []

		self.style = NodeStyle()

		self.showSplits = False
		self.showNull   = False

	def isCompound(self, node):
		return node.isSlot() and len(self.cluster[node.canonical()]) > 1

	def shouldSplit(self, node):
		return isinstance(node, (graph.ExistingNode, graph.NullNode, graph.Entry, graph.Exit))

	def compoundStyle(self, node):
		cluster =  self.cluster[node.canonical()]
		label = "\\n".join([self.style(child)['label'] for child in cluster])
		return dict(label=label, shape='box', style='filled', fillcolor=self.style.compoundColor, fontsize=8)

	def node(self, node, parent=None):
		if self.shouldSplit(node):
			key = (node, parent)
		else:
			key = node

		if key not in self.nodes:
			if self.isCompound(node):
				settings = self.compoundStyle(node)
			else:
				settings = self.style(node)
			result = pydot.Node(id(key), **settings)
			self.g.add_node(result)
			self.nodes[key] = result
		else:
			result = self.nodes[key]

		return result

	def edge(self, src, dst, style='solid'):
		if src.isSlot():
			if not self.showSplits: src  = src.canonical()
			slot = src
		else:
			if not self.showSplits: dst  = dst.canonical()
			slot = dst

		if not self.showNull and slot.isNull(): return

		# If this is not the canonical representative of a slot cluster, skip it
		if not self.cluster.isCanonical(slot.canonical()):
			return
		
		color = self.lineColor(slot)
		
		srcnode = self.node(src, dst)
		dstnode = self.node(dst, src)
		self.g.add_edge(pydot.Edge(srcnode, dstnode, color=color, style=style))


	@dispatch(graph.FieldNode, graph.LocalNode, graph.ExistingNode, graph.NullNode, graph.PredicateNode)
	def handleSlotNode(self, node):
		for forward in node.forward():
			self.mark(forward)

	def lineColor(self, node):
		if self.isCompound(node):
			return self.style.compoundLineColor
		elif isinstance(node, graph.LocalNode):
			return self.style.localLineColor
		elif isinstance(node, graph.FieldNode):
			return self.style.heapLineColor
		elif isinstance(node, graph.PredicateNode):
			return self.style.predicateLineColor
		elif isinstance(node, graph.ExistingNode):
			return self.style.existingLineColor
		else:
			return 'black'


	@dispatch(graph.Merge)
	def handleMerge(self, node):
		for reverse in node.reverse():
			assert reverse.isUse(node)
			self.edge(reverse, node)

		for forward in node.forward():
			assert forward.isDefn(node)
			self.edge(node, forward)
			self.mark(forward)

	@dispatch(graph.Split)
	def handleSplit(self, node):
		if self.showSplits:
			for reverse in node.reverse():
				assert reverse.isUse(node)
				self.edge(reverse, node)
	
		for forward in node.forward():
			assert forward.isDefn(node)
			if self.showSplits: self.edge(node, forward)
			self.mark(forward)

	@dispatch(graph.Gate)
	def handleGate(self, node):
		for reverse in node.reverse():
			assert reverse.isUse(node)
			self.edge(reverse, node)

		for forward in node.forward():
			assert forward.isDefn(node)
			self.edge(node, forward)
			self.mark(forward)


	@dispatch(graph.GenericOp)
	def handleGenericOp(self, node):
		# In
		for slot in node.localReads.itervalues():
			assert slot.isUse(node)
			self.edge(slot, node)

		for slot in node.heapReads.itervalues():
			assert slot.isUse(node)
			self.edge(slot, node)

		for slot in node.heapPsedoReads.itervalues():
			assert slot.isUse(node)
			self.edge(slot, node, style='dotted')

		slot = node.predicate
		assert slot.isUse(node)
		self.edge(slot, node)

		# Out
		for slot in node.localModifies:
			assert slot.isDefn(node)
			self.edge(node, slot)
			self.mark(slot)

		for slot in node.heapModifies.itervalues():
			assert slot.isDefn(node)
			self.edge(node, slot)
			self.mark(slot)

		for slot in node.predicates:
			assert slot.isDefn(node)
			self.edge(node, slot)
			self.mark(slot)


	@dispatch(graph.Entry)
	def handleEntry(self, node):
		for forward in node.forward():
			assert forward.isDefn(node)
			self.edge(node, forward)
			self.mark(forward)


	@dispatch(graph.Exit)
	def handleExit(self, node):
		for reverse in node.reverse():
			assert reverse.isUse(node)
			self.edge(reverse, node)


	def mark(self, node):
		assert node is not None
		if node not in self.processed:
			self.processed.add(node)
			self.queue.append(node)

	def process(self, dataflow):
		# Mark the entry nodes
		self.mark(dataflow.entry)
		for e in dataflow.existing.itervalues():
			self.mark(e)
		self.mark(dataflow.null)
		self.mark(dataflow.entryPredicate)

		# Process
		while self.queue:
			current = self.queue.pop()
			self(current)


class IntersectionFind(object):
	def __init__(self):
		self.lut = {}

	def _updateCluster(self, cluster):
		cluster = tuple(sorted(frozenset(cluster)))
		for node in cluster:
			self.lut[node] = cluster

	def update(self, nodes):
		nodes = set(nodes)
	
		newNodes = []
	
		while nodes:
			current = nodes.pop()
			
			if current not in self.lut:
				newNodes.append(current)
			else:
				cluster = self.lut[current]
				
				keep    = []
				discard = []
	
				for other in cluster:
					if other is current:
						keep.append(other)
					elif other in nodes:
						keep.append(other)
						nodes.remove(other)
					else:
						discard.append(other)
	
				if discard:
					self._updateCluster(keep)
					self._updateCluster(discard)
		
		if newNodes:
			# Join the newly discovered nodes
			self._updateCluster(newNodes)

	def isCanonical(self, node):
		if node in self.lut:
			return self.lut[node][0] == node
		else:
			return True

	def __getitem__(self, key):
		return self.lut[key]

class ClusterNodes(object):
	def __init__(self):
		self.cluster = IntersectionFind()

	def handleGroup(self, nodes):
		# Make the nodes canonical
		nodes = [node.canonical() for node in nodes]
		self.cluster.update(nodes)
	
	def handleNode(self, node):
		if node.isOp() and not node.isSplit():
			self.handleGroup(node.reverse())
			self.handleGroup(node.forward()) 
	
	def process(self, dataflow):
		pending = set(dataflow.entry.modifies.itervalues())
		processed = set()

		self.handleGroup(dataflow.entry.modifies.itervalues())

		while pending:
			current = pending.pop()
			processed.add(current)
			
			self.handleNode(current)
			
			for next in current.forward():
				if next not in processed:
					pending.add(next)

		return self.cluster

	def dump(self):
		for node, cluster in self.cluster.lut.iteritems():
			if self.cluster.isCanonical(node):
				print node
				if len(cluster) > 1:
					for child in cluster:
						print '\t', child
				print


def dumpGraph(directory, name, format, g, prog='dot'):
	s = g.create(prog=prog, format=format)
	filesystem.writeBinaryData(directory, name, format, s)

@async_limited(2)
def evaluateDataflow(dataflow, directory, name):
	cluster = ClusterNodes().process(dataflow)
	
	g = pydot.Dot(graph_type='digraph')
	dtd = DataflowToDot(g, cluster)
	dtd.process(dataflow)

	dumpGraph(directory, name, 'svg', g)
