import pydot
from util.io import filesystem

from util.typedispatch import *
from analysis.cfgIR.cfg import *

from language.python import ast
from util.asttools import astpprint

from util.application.async import *


class CFGIRStyle(TypeDispatcher):
	branchColor = 'cyan'
	mergeColor  = 'magenta'
	blockColor  = 'white'
	typeSwitchColor  = 'lightgoldenrod'
	suiteColor  = 'lightseagreen'

	def opText(self, op):
		return repr(op)
		op = op.op
		if isinstance(op, ast.TypeSwitch):
			label = op.__class__.__name__
		else:
			label = astpprint.toString(op, eol='\\n')

	@dispatch(CFGBlock)
	def handleBlock(self, node):
		label = "\\n".join([self.opText(op) for op in node.ops])

		return dict(label=label, shape='box', style='filled', fillcolor=self.blockColor, fontsize=8)

	@dispatch(CFGBranch)
	def handleBranch(self, node):
		return dict(label=self.opText(node.op), shape='triangle', style='filled', fillcolor=self.branchColor, fontsize=8)


	@dispatch(CFGMerge)
	def handleMerge(self, node):
		return dict(label='merge', shape='invtriangle', style='filled', fillcolor=self.mergeColor, fontsize=8)


	@dispatch(CFGTypeSwitch)
	def handleTypeSwitch(self, node):
		return dict(label="type switch", shape='box', style='filled', fillcolor=self.typeSwitchColor, fontsize=8)


	@dispatch(CFGSuite)
	def handleSuite(self, node):
		return dict(label="suite", shape='box', style='filled', fillcolor=self.suiteColor, fontsize=8)


	@dispatch(CFGEntry, CFGExit)
	def handleEntryExit(self, node):
		return dict(shape='point')


class CFGIRDumper(TypeDispatcher):
	def __init__(self):
		self.g = pydot.Dot(graph_type='digraph')
		self.nodes = {}
		self.style = CFGIRStyle()

		self._cluster = {None:self.g}

	def cluster(self, node):
		if node not in self._cluster:
			c = pydot.Cluster(str(id(node)), **self.style(node))
			parent = self.cluster(node.parent)
			parent.add_subgraph(c)
			self._cluster[node] = c
		else:
			c = self._cluster[node]
		return c

	def node(self, node):
		if node.isCompound(): return self.cluster(node)

		key = node
		if key not in self.nodes:
			cluster = self.cluster(node.parent)

			settings = self.style(node)
			result = pydot.Node(str(id(key)), **settings)
			cluster.add_node(result)
			self.nodes[key] = result
		else:
			result = self.nodes[key]

		return result

	def nodeEntry(self, node):
		if node.isCompound(): node = node.entry
		return self.node(node)

	def nodeExit(self, node):
		if node.isCompound(): node = node.exit
		return self.node(node)

	def edge(self, src, dst, color='black', style='solid', **kargs):
		srcnode = self.nodeExit(src)
		dstnode = self.nodeEntry(dst)
		self.g.add_edge(pydot.Edge(srcnode, dstnode, color=color, style=style, **kargs))

	def backedge(self, src, dst, color='black', style='solid', **kargs):
		srcnode = self.nodeEntry(src)
		dstnode = self.nodeExit(dst)
		self.g.add_edge(pydot.Edge(srcnode, dstnode, color=color, style=style, **kargs))


	@dispatch(CFGBlock)
	def visitBlock(self, node):
		print node
		for op in node.ops:
			print '\t', op
		print

	@dispatch(CFGBranch)
	def visitBranch(self, node):
		print node
		print node.op
		print

	@dispatch(CFGMerge)
	def visitMerge(self, node):
		print node
		print

	@dispatch(CFGEntry, CFGExit)
	def visitOK(self, node):
		pass

	@dispatch(CFGTypeSwitch)
	def visitTypeSwitch(self, node):
		print node
		print node.switch
		print node.cases
		print node.merge
		print


	def handleForward(self, node):
		for next in node.iternext():
			self.edge(node, next)
			self.mark(next)

	def handleReverse(self, node):
		for prev in node.iterprev():
			self.backedge(node, prev, color='red', constraint=False)

	def mark(self, node):
		if node is not None and node not in self.processed:
			self.processed.add(node)
			self.pending.add(node)

	def process(self, node):
		self.pending   = set()
		self.processed = set()
		self.mark(node)
		while self.pending:
			current = self.pending.pop()
			#self(current)

			self.node(current)
			self.handleForward(current)
			self.handleReverse(current)

			if current.isCompound():
				self.mark(current.entry)



@async_limited(2)
def dumpGraph(directory, name, format, g, prog='dot'):
	s = g.create(prog=prog, format=format)
	filesystem.writeBinaryData(directory, name, format, s)

def process(compiler, entry, directory, name):
	cfgird = CFGIRDumper()
	cfgird.process(entry)
	dumpGraph(directory, name+'-cfg', 'svg', cfgird.g)
