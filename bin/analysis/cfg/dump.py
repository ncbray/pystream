import pydot
from util.typedispatch import *

from util.io import filesystem

from . import graph as cfg

def makeStr(s):
	s = s.replace('"', '\\"')
	s = s.replace('\n', '\\n')
	return '"%s"' % s

class NodeStyle(TypeDispatcher):
	suiteColor = 'lightyellow'
	switchColor = 'cyan'
	mergeColor = 'magenta'
	yieldColor = 'aliceblue'

	stateColor = 'green'


	@dispatch(cfg.Entry, cfg.Exit)
	def handleTerminal(self, node):
		return dict(shape='point', fontsize=8)

	@dispatch(cfg.Suite)
	def handleSuite(self, node):
		label = makeStr("\n".join([repr(op) for op in node.ops]))
		return dict(label=label, shape='box', style='filled', fillcolor=self.suiteColor, fontsize=8)

	@dispatch(cfg.Switch)
	def handleSwitch(self, node):
		label = makeStr(repr(node.condition))
		return dict(label=label, shape='trapezium', style='filled', fillcolor=self.switchColor, fontsize=8)

	@dispatch(cfg.Merge)
	def handleMerge(self, node):
		label = makeStr("\n".join([repr(phi) for phi in node.phi]))
		return dict(label=label, shape='invtrapezium', style='filled', fillcolor=self.mergeColor, fontsize=8)

	@dispatch(cfg.Yield)
	def handleYield(self, node):
		return dict(label='yield', shape='circle', style='filled', fillcolor=self.yieldColor, fontsize=8)


	@dispatch(cfg.State)
	def handleState(self, node):
		label = repr(node.name)
		return dict(label=label, shape='doublecircle', style='filled', fillcolor=self.stateColor, fontsize=8)


class CFGToDot(TypeDispatcher):
	def __init__(self, g):
		self.g		 = g
		self.nodes	 = {}
		self.regions = {}
		self.processed = set()
		self.queue	 = []

		self.style = NodeStyle()

	def node(self, node):
		key = node

		if key not in self.nodes:
			node.sanityCheck()
			settings = self.style(node)
			result = pydot.Node(id(key), **settings)

			region = self.region(node)

			region.add_node(result)
			self.nodes[key] = result
		else:
			result = self.nodes[key]

		return result

	def region(self, node):
		region = node.region
		if region not in self.regions:
			result = pydot.Cluster(str(id(region)))
			self.regions[region] = result

			if region is not None:
				parent = self.region(region)
				parent.add_subgraph(result)
			else:
				self.g.add_subgraph(result)
		else:
			result = self.regions[region]

		return result

	def edge(self, src, dst, style='solid', color='black'):
		if src is None or dst is None: return

		srcnode = self.node(src)
		dstnode = self.node(dst)
		self.g.add_edge(pydot.Edge(srcnode, dstnode, color=color, style=style))


	colors = {'normal':'green', 'fail':'yellow', 'error':'red', 'true':'cyan', 'false':'purple'}

	@defaultdispatch
	def default(self, node):
		for name, child in node.next.iteritems():
			if name == 'fail' and child is self.failIgnore:
				continue
			elif name == 'error' and child is self.errorIgnore:
				continue

			self.mark(child)
			self.edge(node, child, color=self.colors.get(name, 'black'))

#		for prev in node.reverse():
#			self.edge(node, prev, color='red')


	@dispatch(type(None))
	def visitNone(self, node):
		pass

	def mark(self, node):
		assert node is not None
		if node not in self.processed:
			self.processed.add(node)
			self.queue.append(node)

	def process(self, code):
		#self.failIgnore  = code.failTerminal
		self.failIgnore = None

		self.errorIgnore = code.errorTerminal
		self.mark(code.entryTerminal)

		while self.queue:
			current = self.queue.pop()
			self(current)

def dumpGraph(directory, name, format, g, prog='dot'):
	s = g.create(prog=prog, format=format)
	filesystem.writeBinaryData(directory, name, format, s)

def evaluate(compiler, cfg):
	g = pydot.Dot(graph_type='digraph')

	ctd = CFGToDot(g)
	ctd.process(cfg)

	directory = 'summaries'
	name = cfg.code.name

	dumpGraph(directory, name, 'svg', g)
