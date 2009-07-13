from util.typedispatch import *
from language.python import ast

import os.path
import pydot
import util.filesystem
from language.base import astpprint

import analysis.dataflowIR.graph as graph


class NodeStyle(TypeDispatcher):
	localColor     = 'lime'
	localLineColor = 'darkgreen'

	existingColor  = 'orange'

	nullColor = 'gray'

	heapColor = 'aliceblue'
	heapLineColor = 'blue'

	opColor = 'lightyellow'

	splitColor = 'cyan'
	mergeColor = 'magenta'
	gateColor  = 'purple'

	predicateColor = 'red'
	predicateLineColor = 'darkred'

	@dispatch(graph.Entry, graph.Exit)
	def handleTerminal(self, node):
		return dict(shape='point', fontsize=8)

	@dispatch(graph.FieldNode)
	def handleFieldNode(self, node):
		label = "%r\\n%r" % (node.name.object, node.name.slotName)
		return dict(label=label, style='filled', fillcolor=self.heapColor, fontsize=8)

	@dispatch(graph.LocalNode)
	def handleLocalNode(self, node):
		label = "\\n".join(repr(name) for name in node.names)
		return dict(label=label, style='filled', fillcolor=self.localColor, fontsize=8)

	@dispatch(graph.PredicateNode)
	def handlePredicateNode(self, node):
		label = str(node.name)
		return dict(label=label, style='filled', fillcolor=self.predicateColor, fontsize=8)


	@dispatch(graph.ExistingNode)
	def handleExistingNode(self, node):
		label = str(node.name)
		return dict(label=label, style='filled', fillcolor=self.existingColor, fontsize=8)

	@dispatch(graph.NullNode)
	def handleNullNode(self, node):
		label = "NULL"
		return dict(label=label, style='filled', fillcolor=self.nullColor, fontsize=8)

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
	def __init__(self, g):
		self.g = g
		self.nodes     = {}
		self.processed = set()
		self.queue     = []

		self.style = NodeStyle()

	def shouldSplit(self, node):
		return isinstance(node, (graph.ExistingNode, graph.NullNode, graph.Entry, graph.Exit))

	def node(self, node, parent=None):
		if self.shouldSplit(node):
			key = (node, parent)
		else:
			key = node

		if key not in self.nodes:
			settings = self.style(node)
			result = pydot.Node(id(key), **settings)
			self.g.add_node(result)
			self.nodes[key] = result
		else:
			result = self.nodes[key]

		return result

	def edge(self, src, dst, color='black', style='solid'):
		srcnode = self.node(src, dst)
		dstnode = self.node(dst, src)
		self.g.add_edge(pydot.Edge(srcnode, dstnode, color=color, style=style))


	@dispatch(graph.FieldNode, graph.LocalNode, graph.ExistingNode, graph.NullNode, graph.PredicateNode)
	def handleSlotNode(self, node):
		for forward in node.forward():
			self.mark(forward)

	def lineColor(self, node):
		if isinstance(node, graph.LocalNode):
			return self.style.localLineColor
		elif isinstance(node, graph.FieldNode):
			return self.style.heapLineColor
		elif isinstance(node, graph.PredicateNode):
			return self.style.predicateLineColor
		else:
			return 'black'


	@dispatch(graph.Merge, graph.Split)
	def handleOpNode(self, node):
		for reverse in node.reverse():
			assert reverse.isUse(node)
			self.edge(reverse, node, color=self.lineColor(reverse))

		for forward in node.forward():
			assert forward.isDefn(node)
			self.edge(node, forward, color=self.lineColor(forward))
			self.mark(forward)

	@dispatch(graph.Gate)
	def handleGate(self, node):
		for reverse in node.reverse():
			assert reverse.isUse(node)
			self.edge(reverse, node, color=self.lineColor(reverse))

		for forward in node.forward():
			assert forward.isDefn(node)
			self.edge(node, forward, color=self.lineColor(forward))
			self.mark(forward)


	@dispatch(graph.GenericOp)
	def handleGenericOp(self, node):
		# In
		for slot in node.localReads.itervalues():
			assert slot.isUse(node)
			self.edge(slot, node, color=self.style.localLineColor)

		for slot in node.heapReads.itervalues():
			assert slot.isUse(node)
			self.edge(slot, node, color=self.style.heapLineColor)

		for slot in node.heapPsedoReads.itervalues():
			assert slot.isUse(node)
			self.edge(slot, node, color=self.style.heapLineColor, style='dotted')

		slot = node.predicate
		assert slot.isUse(node)
		self.edge(slot, node, color=self.style.predicateLineColor)

		# Out
		for slot in node.localModifies:
			assert slot.isDefn(node)
			self.edge(node, slot, color=self.style.localLineColor)
			self.mark(slot)

		for slot in node.heapModifies.itervalues():
			assert slot.isDefn(node)
			self.edge(node, slot, color=self.style.heapLineColor)
			self.mark(slot)

		for slot in node.predicates:
			assert slot.isDefn(node)
			self.edge(node, slot, color=self.style.predicateLineColor)
			self.mark(slot)


	@dispatch(graph.Entry)
	def handleEntry(self, node):
		for forward in node.forward():
			assert forward.isDefn(node)
			self.edge(node, forward, self.lineColor(forward))
			self.mark(forward)


	@dispatch(graph.Exit)
	def handleExit(self, node):
		for reverse in node.reverse():
			assert reverse.isUse(node)
			self.edge(reverse, node, self.lineColor(reverse))


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


def dumpGraph(name, g, format='svg', prog='dot'):
	s = g.create(prog=prog, format=format)
	fn = name+('.'+format)
	f = open(fn, 'wb')
	f.write(s)
	f.close()
	return fn

def evaluateDataflow(dataflow, directory, name):
	g = pydot.Dot(graph_type='digraph')
	dtd = DataflowToDot(g)
	dtd.process(dataflow)

	util.filesystem.ensureDirectoryExists(directory)
	dumpGraph(os.path.join(directory, name), g, prog='dot')