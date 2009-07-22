import collections

def colorGraph(G):
	# Assumes G[node] -> iterable(nodes), a in G[b] implies b in G[a]

	solution   = {}
	numColors  = 0
	constraint = collections.defaultdict(set)
	group      = []


	pending   = set()
	remaining = {}

	for node, values in G.iteritems():
		remaining[node] = len(values)
		pending.add(node)

	while pending:
		# Select the next node to color
		# HACK search for node with max remaining neighbors.
		maxRemain = -1
		maxNode   = None
		for node in pending:
			if remaining[node] > maxRemain:
				maxNode   = node
				maxRemain = remaining[node]
		assert maxNode is not None
		pending.remove(maxNode)

		# Determine the color of the node
		current = maxNode
		for color in range(numColors):
			if color not in constraint[current]:
				break
		else:
			color = numColors
			numColors += 1
			group.append([])

		solution[current] = color
		group[color].append(current)
		for other in G[current]:
			remaining[other] -= 1
			constraint[other].add(color)

	return solution, group, numColors
