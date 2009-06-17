import util.graphalgorithim.basic

# Based on the paper:
# Efficient Implementation of Lattice Operations
# HASSAN AIT-KACI, ROBERT BOYER, PATRICK LINCOLN, and ROGER NASR

class Lattice(object):
	def __init__(self, G, head):
		self.G    = G
		self.head = head

		rG = util.graphalgorithim.basic.reverseDirectedGraph(G)

		pending   = set((self.head,))
		processed = set()

		self.encoding = {}
		self.decoding = {}

		p = 0

		# Just do reverse post order?
		while pending:
			current = pending.pop()
			processed.add(current)


			encoding = reduce(lambda a, b: a|b, [self.encoding[child] for child in rG.get(current, ())], 0)

			if encoding in self.decoding:
				encoding |= 2**p
				p += 1

			self.encoding[current]  = encoding
			self.decoding[encoding] = current


			print current, ' - ', "%x" % encoding

			for child in G.get(current, ()):
				if processed.issuperset(rG.get(child, ())):
					pending.add(child)


	def decode(self, code):
		if code in self.decoding:
			return (self.decoding[code],)
		else:
			assert False

	def lub(self, inital, *args):
		current = self.encoding[inital]
		for arg in args:
			current |= self.encoding[arg]

		print "LUB %x" % current

		return self.decode(current)

	def glb(self, inital, *args):
		current = self.encoding[inital]
		for arg in args:
			current &= self.encoding[arg]

		print "GLB %r, %s - %x" % (inital, ", ".join([repr(arg) for arg in args]), current)

		return self.decode(current)
