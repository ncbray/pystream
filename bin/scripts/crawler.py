from modulefinder import ModuleFinder

mf = ModuleFinder()
mf.run_script('runtests.py')



##from clustering.cluster import *
##from clustering.pairloader import loadPairs
##
##leafs = mf.modules.values()
##d, n, l = createRandomHG(range(len(leafs)))
##
##
##
##for leaf in enumerate(leafs: # Add edges
##	for imp in leaf.imports:
##		addEdge(l[src], l[dst])


from util import dot

g = dot.Digraph(overlap='scale')

def allowModule(m):
	if m.__path__:
		assert len(m.__path__) == 1, m
		return m.__path__[0].find('Python25') == -1

	return True

for name, module in mf.modules.iteritems():
	if allowModule(module):
		g.node(id(module), label=name)

		for imp in module.imports:
			if allowModule(imp):
				g.edge(id(imp), id(module))


dot.createGraphic(g, 'imports')
