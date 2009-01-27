import os.path
import pydot
import util.graphalgorithim.dominator
from analysis.astcollector import getOps

# HACK duplicated code
def codeShortName(code):
	if isinstance(code, str):
		name = func
		args = []
		vargs = None
		kargs = None
	elif code is None:
		name = 'external'
		args = []
		vargs = None
		kargs = None
	else:
		name = code.name
		args = list(code.parameternames)
		vargs = None if code.vparam is None else code.vparam.name
		kargs = None if code.kparam is None else code.kparam.name

	if vargs is not None: args.append("*"+vargs)
	if kargs is not None: args.append("**"+kargs)

	return "%s(%s)" % (name, ", ".join(args))


def dumpGraph(name, g, format='svg', prog='dot'):
	s = g.create(prog=prog, format=format)
	fn = name+('.'+format)
	f = open(fn, 'wb')
	f.write(s)
	f.close()
	return fn

def dump(data, entryPoints, links, reportDir):
	stack = []
	processed = set()
	for func, funcobj, args in entryPoints:
		code = func.code
		info = data.db.functionInfo(code)
		for context in info.contexts:
			context = None
			key = (code, context)
			if key not in processed:
				stack.append(key)
				processed.add(key)


	invokeLUT = {}

	while stack:
		node =  stack.pop()
		code, context = node
		ops, lcls = getOps(code)

		invokeLUT[node] = set()

		info = data.db.functionInfo(code)
		for op in ops:
			opinfo = info.opInfo(op)
			if context is None:
				cinfo = opinfo.merged
			else:
				cinfo = opinfo.context(context)
			invokes = cinfo.invokes
			for c, f in invokes:
				c = None
				key = (f, c)
				invokeLUT[node].add(key)
				if key not in processed:
					stack.append(key)
					processed.add(key)

	head = None
	util.graphalgorithim.dominator.makeSingleHead(invokeLUT, head)
	tree, idoms = util.graphalgorithim.dominator.dominatorTree(invokeLUT, head)

	#idons = {}

	g = pydot.Dot(graph_type='digraph',
			#overlap='scale',
			rankdir='LR',
			#concentrate=True,
			)

	def makeNode(tree, sg, node):
		if node is not None:
			code, context = node

			if data.db.functionInfo(code).descriptive:
				nodecolor = "#FF3333"
			elif code.selfparam is None:
				nodecolor = '#BBBBBB'
			else:
				nodecolor = '#33FF33'
			sg.add_node(pydot.Node(node, label=codeShortName(code), shape='box', style="filled", fontsize=8, fillcolor=nodecolor, URL=links.codeRef(*node)))


		children = tree.get(node)
		if children:
			csg = pydot.Cluster(str(id(node)))#rank='same')
			sg.add_subgraph(csg)
			for child in children:
				makeNode(tree, csg, child)

	makeNode(tree, g, head)

	for src, dsts in invokeLUT.iteritems():
		if src is head: continue
		for dst in dsts:
			if idoms.get(dst) is src:
				weight = 10
			else:
				weight = 1
			g.add_edge(pydot.Edge(src, dst, weight=weight))

	dumpGraph(os.path.join(reportDir, 'invocations'), g, prog='dot')
	#g.write('dump.txt')