import os.path
import pydot
import util.graphalgorithim.dominator
from analysis.dump import dumputil
from util.async import *
import util.filesystem

def dumpGraph(directory, name, format, g, prog='dot'):
	s = g.create(prog=prog, format=format)
	util.filesystem.writeBinaryData(directory, name, format, s)

@async
def dump(compiler, liveInvoke, links, reportDir):
	# Filter out primitive nodes
	def keepCode(code):
		return code is None or not code.annotation.primitive

	head = None
	invokeLUT = {}
	for src, dst in liveInvoke.iteritems():
		if keepCode(src):
			invokeLUT[src] = [code for code in dst if keepCode(code)]

	# Make dominator tree
	tree, idoms = util.graphalgorithim.dominator.dominatorTree(invokeLUT, head)

	# Start graph creation
	g = pydot.Dot(graph_type='digraph',
			#overlap='scale',
			rankdir='LR',
			#concentrate=True,
			)

	# Create nodes
	def makeNode(tree, sg, node):
		if node is not None:
			code = node

			if not code.isStandardCode():
				nodecolor = "#4444FF"
			elif code.annotation.descriptive:
				nodecolor = "#FF3333"
			elif code.codeparameters.selfparam is None:
				nodecolor = '#BBBBBB'
			else:
				nodecolor = '#33FF33'
			sg.add_node(pydot.Node(str(id(node)), label=dumputil.codeShortName(code),
				shape='box', style="filled", fontsize=8,
				fillcolor=nodecolor, URL=links.codeRef(node, None)))
		else:
			sg.add_node(pydot.Node(str(id(node)), label="entry",
				shape='point', style="filled", fontsize=8))

		children = tree.get(node)
		if children:
			csg = pydot.Cluster(str(id(node)))
			sg.add_subgraph(csg)
			for child in children:
				makeNode(tree, csg, child)

	makeNode(tree, g, head)

	# Create edges
	for src, dsts in invokeLUT.iteritems():
		#if src is head: continue
		for dst in dsts:
			if idoms.get(dst) is src:
				weight = 10
			else:
				weight = 1
			g.add_edge(pydot.Edge(str(id(src)), str(id(dst)), weight=weight))

	# Output
	dumpGraph(reportDir, 'invocations', 'svg', g)
