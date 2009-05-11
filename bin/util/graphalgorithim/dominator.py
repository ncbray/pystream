from . import basic

class ReversePostorderCrawler(object):
	def __init__(self, G, head):
		self.G = G
		self.head = head

		self.all = set(G.iterkeys())

		self.processed = set((self.head,))
		self.order = []

		for next in self.G[self.head]:
			self(next)

		# Look for inaccesable cycles
		remaining = self.all-self.processed
		while remaining:
			newEntry = remaining.pop()
			self.G[head] = set(self.G[head])
			self.G[head].add(newEntry)
			self(newEntry)
			remaining = self.all-self.processed

		# Finally, the head
		self.order.append(self.head)

		self.order.reverse()

	def __call__(self, node):
		if node in self.processed: return

		# Ugly: maintain our own stack, as Python's is limited.
		# Based on PADS
		self.processed.add(node)
		stack = [(node, iter(self.G.get(node, ())))]
		while stack:
			parent,children = stack[-1]
			try:
				child = children.next()
				if child not in self.processed:
					self.processed.add(child)
					stack.append((child, iter(self.G.get(child, ()))))
			except StopIteration:
				self.order.append(stack[-1][0])
				stack.pop()

def intersect(doms, b1, b2):
	finger1 = b1
	finger2 = b2
	while finger1 != finger2:
		while finger1 > finger2:
			finger1 = doms[finger1]

		while finger2 > finger1:
			finger2 = doms[finger2]
	return finger1

def dominatorTree(G, head):
	order = ReversePostorderCrawler(G, head).order

	# Make forward and reverse maps G <-> reverse postorder
	forward = {}
	reverse = {}
	for i, node in enumerate(order):
		forward[node] = i
		reverse[i] = node

	# Find the predicesors, in reverse postorder space.
	pred = {}
	for node, nexts in G.iteritems():
		i = forward[node]
		for next in nexts:
			n = forward[next]

			# Eliminate self-cycles.
			if i == n: continue

			if n not in pred:
				pred[n] = [i]
			else:
				pred[n].append(i)

	# Setup for calculation
	count = len(order)
	doms = [None for i in range(count)]

	# Special case the head
	doms[0] = 0

	# Calculate a fixedpoint solution
	changed = True
	while changed:
		changed = False
		for node in range(1, count):
			# Find an inital value for the immediate dominator
			if doms[node] is None:
				new_idom = min(pred[node])
				assert new_idom < node
			else:
				new_idom = doms[node]

			# Refine the immediate dominator,
			# make it consistant with the predicesors.
			for p in pred[node]:
				if doms[p] is not None:
					new_idom = intersect(doms, new_idom, p)

			# Check if the immediate dominator has changed.
			if doms[node] is not new_idom:
				assert doms[node] is None or new_idom < doms[node]
				doms[node] = new_idom
				changed = True


	# Map the solution onto the original graph.
	idoms = {}
	tree  = {}
	for node, idom in enumerate(doms):
		if node is 0: continue # Skip the head
		node = reverse[node]
		idom = reverse[idom]
		idoms[node] = idom

		if idom not in tree:
			tree[idom] = [node]
		else:
			tree[idom].append(node)
	return tree, idoms



def makeSingleHead(G, head):
	entryPoints = basic.findEntryPoints(G)
	G[head] = entryPoints



if __name__ == '__main__':
	G = {0:(1, 2), 1:(3,), 2:(3,), 3:(4, 5), 4:(6,), 5:(6,)}

	head = None
	makeSingleHead(G, head)
	print dominatorTree(G, head)
