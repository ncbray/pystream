import pydot
import util.filesystem

from util.typedispatch import *
from . cfg import *

class CFGIRStyle(TypeDispatcher):
	branchColor = 'cyan'
	mergeColor  = 'magenta'
	blockColor  = 'white'

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


class CFGIRDumper(TypeDispatcher):
	def __init__(self):
		self.g = pydot.Dot(graph_type='digraph')
		self.nodes = {}
		self.style = CFGIRStyle()

	def node(self, node):
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
		srcnode = self.node(src)
		dstnode = self.node(dst)
		self.g.add_edge(pydot.Edge(srcnode, dstnode, color=color, style=style))

	@dispatch(CFGBlock)
	def visitBlock(self, node):
		print node
		for op in node.ops:
			print '\t', op
		print

		if node.next:
			self.edge(node, node.next)
			self.mark(node.next)

#		if node.prev:
#			self.edge(node, node.prev, color='red')


	@dispatch(CFGBranch)
	def visitBranch(self, node):
		print node
		print node.op
		print

		for next in node.next:
			self.edge(node, next)
			self.mark(next)

		#self.edge(node, node.prev, color='red')



	@dispatch(CFGMerge)
	def visitMerge(self, node):
		print node
		print

		if node.next:
			self.edge(node, node.next)
			self.mark(node.next)

#		for prev in node.prev:
#			self.edge(node, prev, color='red')


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
			self.node(current)
			self(current)

def dumpGraph(directory, name, format, g, prog='dot'):
	s = g.create(prog=prog, format=format)
	util.filesystem.writeBinaryData(directory, name, format, s)

def process(compiler, entry, directory, name):
	cfgird = CFGIRDumper()
	cfgird.process(entry)
	dumpGraph(directory, name+'-cfg', 'svg', cfgird.g)
