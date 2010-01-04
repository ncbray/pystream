def loadPairs(fn):
	f = open(fn)

	count = 0
	edges = []

	for line in f:
		# Pairs start at "1", so shift.
		edge =  tuple([int(node)-1 for node in line.split()])
		edges.append(edge)
		count = max(count, *edge)

	f.close()

	return count+1, edges
