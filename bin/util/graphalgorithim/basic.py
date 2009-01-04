def reverseDirectedGraph(G):
	out = {}
	for node, nexts in G.iteritems():
		for next in nexts:
			if next not in out:
				out[next] = [node]
			else:
				out[next].append(node)
	return out

def findEntryPoints(G):
	entryPoints = set(G.iterkeys())
	for nexts in G.itervalues():
		for next in nexts:
			if next in entryPoints:
				entryPoints.remove(next)
	return list(entryPoints)
