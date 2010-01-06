class MergeError(Exception):
	pass

class MergeOptimizer(object):
	def emitTransfer(self, src, dst):
		src = self.remap.get(src, src)
		self.result.append((src, dst))

	def save(self, node):
		if node not in self.remap:
			t = self.genTemp(node)
			self.remap[node] = t
			self.temporaries.append(t)

	def visit(self, node):
		if node in self.g:
			src = self.g.pop(node)
			self.current.add(node)

			self.visit(src)

			self.emitTransfer(src, node)

			if node in self.remap:
				self.result.append((node, self.remap[node]))
				del self.remap[node]

			self.current.remove(node)

		elif node in self.current:
			# Backedge
			self.save(node)

	def buildReverseGraph(self, merges):
		# The reverse graph is simpler than the forward graph because
		# names will only have one definition, but may have multiple uses
		entries = []
		for src, dst in merges:
			if dst in self.g:
				raise MergeError, "Multiple definitions of %r" % dst
			self.g[dst] = src

			entries.append(dst)
		return entries

	def process(self, merges, genTemp):
		self.genTemp = genTemp
		self.g  = {}
		entries = self.buildReverseGraph(merges)

		self.result = []
		self.temporaries = []
		self.remap   = {}
		self.current = set()

		# Generate reverse postorder
		entries.reverse()
		for node in entries:
			self.visit(node)
		self.result.reverse()

# Given a list of simultanious assignments, generate a list of sequential
# assignments, inserting temporaries as needed.
# merges: should be a list of tuples - (src, dst)*
# genTemp: (node)=>node should be a callback that creates a temporary name
# compatable with the name passed to it.
# Returns the list of sequntial merges, and a list of temporaries.
def serializeMerges(merges, genTemp):
	mo = MergeOptimizer()
	mo.process(merges, genTemp)
	return mo.result, mo.temporaries
