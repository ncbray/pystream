import os
import re

__all__ = 'Digraph', 'Style', 'createGraphic'

makeescape = re.compile(r'[\n\"]')

lut = {'\n':r'\n', '\t':r'\t', '"':r'\"'}

def escapeField(s):
	return makeescape.sub(lambda c: lut[c.group()], str(s))

###
# digraph/graph
# ->/--
# different exe

class Subgraph(object):
	__slots__ = 'graphtype', 'name', 'attr', 'subgraphs', 'nodes', 'nameLUT', 'edges', 'parent', 'nodetype', 'edgetype'

	def __init__(self, graphtype, name, nodetype=None, edgetype=None, **attr):
		self.graphtype = graphtype

		self.name = name
		self.attr = attr
		self.parent = None

		self.subgraphs = []
		self.nodes = []
		self.edges = []
		self.nameLUT = {}
		
		self.nodetype = nodetype
		self.edgetype = edgetype

	def isDirected(self):
		return self.graphtype == 'digraph'

	def createDotFile(self, fo):
		if isinstance(fo, str): fo = open(fo, 'w')
		self.outputDot(fo)

	def outputDot(self, out, tabs=''):
		indent = tabs + '\t'
		out.write('%s%s "%s" {\n' % (tabs, self.graphtype, escapeField(self.name)))

		#Output attributes
		for k, v in self.attr.iteritems():
			out.write(indent + k + ' = "' + escapeField(v) + '"\n')

		# Output subgraphs
		for sg in self.subgraphs:
			sg.outputDot(out, indent)

		# Output nodes
		if self.nodetype:
			out.write("%snode" % indent)
			dumpAttr(self.nodetype, out)
			out.write(";\n")
			
		self.nodes.sort(key=lambda n: n.style)
		currentStyle = None
		for n in self.nodes:
			if currentStyle != n.style:
				out.write("%snode" % indent)
				dumpAttr(n.style, out)
				out.write(";\n")
				currentStyle = n.style
			n.dump(out, indent)

		# Output edges
		if self.edgetype:
			out.write("%sedge" % indent)
			dumpAttr(self.edgetype, out)
			out.write(";\n")

		self.edges.sort(key=lambda e: e.style)

		directed =  self.isDirected()

		currentStyle = None
		for e in self.edges:
			if currentStyle != e.style:
				out.write("%sedge" % indent)
				dumpAttr(e.style, out)
				out.write(";\n")
				currentStyle = e.style
			e.resolveNodes(self)
			e.dump(out, indent, directed)

		out.write('%s}\n' % (tabs,))

	def subgraph(self, name, **attr):
		name = str(name)
		sg = Subgraph('subgraph', name, **attr)
		sg.parent = self
		self.subgraphs.append(sg)

		if name[:8] == 'cluster_':
			self.registerNode(name, sg)

		return sg

	def cluster(self, name, **attr):
		name = str(name)
		clustername = 'cluster_%s' % name
		sg = self.subgraph(clustername, **attr)
		return sg

	def registerNode(self, name, node):
		self.nameLUT[name] = node
		if self.parent: self.parent.registerNode(name, node)

	def node(self, name, nodetype=None, **attr):
		name = str(name)
		assert not name in self.nameLUT, name
		n = Node(name, nodetype, **attr)
		n.parent = self
		self.nodes.append(n)
		self.registerNode(name, n)
		return n

	def getNode(self, n):		
		if isinstance(n, Node) or isinstance(n, Subgraph):
			return n		
		else:
			n = str(n)
			assert n in self.nameLUT, "Cannot find node " + str(n) + '\n\n' + str(self.nameLUT)
			return self.nameLUT[n]

	def edge(self, n1, n2, edgetype=None, **kargs):
		n1 = str(n1)
		n2 = str(n2)
		if self.parent:
			# Push the edge definition back to the root.
			edgetype = edgetype or self.edgetype
			return self.parent.edge(n1, n2, edgetype, **kargs)
		else:
			nodes = [n1, n2]
			#nodes = [self.getNode(n) for n in nodes]
			e = Edge(nodes, edgetype, **kargs)
			self.edges.append(e)
			return e

class Node(object):
	__slots__ = ('name', 'attr', 'parent', 'style')
	
	validattr = ['bottomlabel', 'color', 'comment', 'distortion', 'fillcolor',
		     'fixedsize', 'fontcolor', 'fontname', 'fontsize', 'group',
		     'height', 'label', 'layer', 'orientation', 'peripheries',
		     'regular', 'shape', 'shapefile', 'sides', 'skew', 'style',
		     'toplabel', 'URL', 'width', 'z']

	def __init__(self, name, nodetype=None, **attr):
		assert isinstance(name, str)
		self.name = name
		self.attr = attr
		self.parent = None
		self.style = nodetype

	def dump(self, out, tabs=''):
		out.write('%s"%s"' % (tabs, escapeField(self.name)))
		if self.attr: dumpAttr(self.attr, out)
		out.write(";\n")

class Edge(object):
	__slots__ = ('nodes', 'attr', 'style')
	
	def __init__(self, nodes, edgetype=None, **attr):
		assert len(nodes) >= 2
		self.nodes = nodes
		self.attr = attr
		self.style = edgetype

	def resolveNodes(self, subgraph):
		self.nodes = [subgraph.getNode(node) for node in self.nodes]

	def dump(self, out, tabs, directed):
		assert len(self.nodes) >= 2


		symbol = '->' if directed else '--'

		out.write('%s"%s"' % (tabs, escapeField(self.nodes[0].name)))
		for i in range(1, len(self.nodes)):
			out.write(' %s "%s"' % (symbol, escapeField(self.nodes[i].name)))

		if self.attr: dumpAttr(self.attr, out)

		out.write(';\n')

def Style(**kargs):
	for k, v in kargs.iteritems():
		assert type(k) == str and type(v) == str
	return kargs

def dumpAttr(attr, out):
	out.write(" [")
	first = True
	for k, v in attr.iteritems():
		v = str(v)
		assert type(k) == str and type(v) == str
		if first:
			out.write('%s="%s"' % (k, escapeField(v)))
			first = False
		else:
			out.write(', %s="%s"' % (k, escapeField(v)))
	out.write("]")

def Digraph(**attr):
	name = 'G'
	return Subgraph('digraph', name, **attr)

def createGraphic(g, name, format='png'):
	dotfile = name + '.dot'
	g.createDotFile(dotfile)
	compileDotFile(name, format)


def compileDotFile(name, format):
	dotfile = name + '.dot'
	imagefile = name + '.' + format
	dot = r'c:\Program Files\ATT\Graphviz\bin\dot.exe'
	#dot = r'c:\Program Files\ATT\Graphviz\bin\neato.exe'

	options = ['-T'+format, '-o'+imagefile, dotfile]
	cmd = ('"%s" ' % dot) + ' '.join(options)
	status = os.system(cmd)

if __name__ == '__main__':
	import sys

	boxish = Style(shape='box')
	dotted = Style(style='dotted', color='red')

	
	g = Digraph('G', edgetype=dotted)
	c1 = g.cluster('sg1')
	c1.node('n1', nodetype=boxish, label='!!!!')
	c1.node('n2')
	
	c2 = g.cluster('sg2')
	c2.node('n3')
	c2.node('n4')

	g.edge('n1', 'n2', 'n3', 'n4', label='n')

	g.createDotFile(sys.stdout)

	createGraphic(g, 'test')
