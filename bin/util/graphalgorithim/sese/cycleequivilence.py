import collections
from . import bracket
from .. import basic

# Explicitly expands the graph so each node consists of an "in", "internal", and "out" node.
# Also creates directed "back" edges, which guarentees the search will find all nodes.
def orderedUndirected(G, start):
	rG = basic.reverseDirectedGraph(G)
	
	nG = {}

	for n1, v in G.iteritems():
		# Forward edges before reverse edges.
		nG[(n1, 'in')] = ((n1, '0'),)+tuple([(n, 'out') for n in rG[n1]])
		nG[(n1, '0')] = ((n1, 'out'), (n1, 'in'))
		nG[(n1, 'out')] = tuple([(n, 'in') for n in v])+((n1, '0'),)

	start = (start, 'out')

	return nG, start



class UndirectedTransformationSearcher(object):
	def search(self, G, start):
		# Expand G

		self.forward    = G
		self.reverse    = basic.reverseDirectedGraph(G)

		startX = (start, 'out')

		#G, startX = orderedUndirected(G, start)
		self.expanded = G
		
		self.processed = set()

		self.head(startX)
		self.__process(startX)

	def children(self, node):
		base, ext = node

		if ext == 'in':
			children = [(base, '0')]
			children.extend([(child, 'out') for child in self.reverse.get(base, ())])
			#children = self.expanded.get(node, ())
		elif ext == 'out':
			children = [(child, 'in') for child in self.forward.get(base, ())]
			children.append((base, '0'))

			#children = self.expanded.get(node, ())
		elif ext == '0':
			children = ((base, 'out'),(base, 'in'))
		else:
			assert False, node

		return children


##	def children(self, node):
##		base, ext = node
##
##		if ext == 'in':
##			yield (base, '0')
##			for child in self.reverse.get(base, ()):
##				yield (child, 'out')
##		elif ext == 'out':
##			for child in self.forward.get(base, ()):
##				yield (child, 'in')
##			yield (base, '0')
##		elif ext == '0':
##			yield (base, 'out')
##			yield (base, 'in')
##		else:
##			assert False, node

	def __process(self, node):
		#assert node not in self.processed, node
		
		self.processed.add(node)

		for child in self.children(node):
			if child in self.processed:
				self.backedge(node, child)
			else:
				self.preorder(node, child)
				self.__process(child)
				self.postorder(node, child)

	def head(self, node):
		pass
	
	def preorder(self,parent,child):
		pass

	def postorder(self,parent,child):
		pass

	def backedge(self,source,destination):
		pass



class CycleEquivilenceSearcher(UndirectedTransformationSearcher):
	def __init__(self,G, head, tail):

		#self.head = head
		#self.tail = tail
		
		self.originalStart = 'start'
		self.originalG = G

		# HACK
		start = self.originalStart
		
		self.current = 0
		self.number = {}
		self.node = {}
		self.queue = []

		# Forward edge or back edge?		
		self.edges = {}

		self.backto 	= collections.defaultdict(set)
		self.backfrom 	= collections.defaultdict(set)
		self.child 	= collections.defaultdict(set)
		self.capping 	= collections.defaultdict(set)
		self.parent 	= collections.defaultdict(lambda:None)

		#self.numberNode(start)
		self.search(G, start)
		self.process()



	def markEdge(self, a, b, state):
		a = self.number[a]
		b = self.number[b]
		index = (a, b) if a<b else (b, a)

		if not index in self.edges:
			self.edges[index] = state
		else:
			assert not (state and self.edges[index] == False)

	def classify(self, a, b):
		a = self.number[a]
		b = self.number[b]

		index = (a, b) if a<b else (b, a)

		return self.edges[index]

	def numberNode(self, node):
		assert not node in self.number
		self.number[node] = self.current
		self.node[self.current] = node
		self.current += 1

	def head(self, node):
		self.numberNode(node)
		
	def preorder(self,parent,child):
		self.numberNode(child)
		self.queue.append(child)
		self.markEdge(parent, child, True)

	def postorder(self,parent,child):
		pass

	def backedge(self,source,destination):
		self.markEdge(source, destination, False)

	

	def classifyEdges(self, n):
		nnum = self.number[n]
		for child in self.children(n):
			cnum = self.number[child]
		
			if not self.classify(n, child):
				if cnum < nnum:
					self.backfrom[n].add(child)
				else:
					self.backto[n].add(child)
			else:
				if cnum > nnum:
					self.child[n].add(child)
				else:
					assert self.parent[n] == None
					self.parent[n] = child

	def findCap(self, n):
		smallestL = []
		largestL  = []
	
		for back in self.backfrom[n]:
			smallestL.append(self.number[back])
		
		for child in self.child[n]:
			smallestL.append(self.high[child])
			largestL.append(self.high[child])

		smallest = min(smallestL)
		self.high[n] = smallest

		if largestL:
			largest = self.node[max(largestL)]
		else:
			# There may be no children...
			largest = None
		
		return largest

	# Caching brackets
	def bracket(self, a, b):
		assert self.number[a] > self.number[b]
		index = (a, b)
		if not index in self.brackets:
			self.brackets[index] = bracket.Bracket(index)
		return self.brackets[index]

	def makeBracketList(self, n):
		bl = bracket.BracketList()
		self.lists[n] = bl

		# Gather child  lists
		for child in self.child[n]:
			cbl = self.lists[child]
			bl.concat(cbl)

		# Remove previous backedges.
		for d in self.backto[n]:
			br = self.bracket(d, n)
			bl.delete(br)

		for d in self.capping[n]:
			br = self.bracket(d, n)
			bl.delete(br)

		# Add eminating backedges
		for a in self.backfrom[n]:
			br = self.bracket(n, a)
			bl.push(br)
			self.recentsize[br] = -1

		cap = self.findCap(n)

		# Add a capping back edge
		if len(self.child[n]) > 1:
			assert cap != None
			br = self.bracket(n, cap)
			bl.push(br)				
			self.recentsize[br] = -1
			self.capping[cap].add(n)
			
		return bl

	def classifyEdge(self, (a, b), cls):
		assert a in self.originalG, a
		assert b in self.originalG, b

		# Make the order match the original graph.
		if not b in self.originalG[a]:
			a, b = b, a
			
		self.CEClass[(a, b)] = cls

	def classifyNode(self, n, cls):
		assert n in self.originalG, n
		self.NQClass[n] = cls

	def classifyBracket(self, n, bl):		
		if bl.size():
			top = bl.top()
			if self.recentsize[top] != bl.size():
				assert bl.size() > 0
				self.recentsize[top] = bl.size()
				self.recentclass[top] = self.currentclass
				self.currentclass += 1

			cls = self.recentclass[top]

			# Only classify edges between inputs and outputs
			parent = self.parent[n]
			if n[1] != '0' and parent[1] != '0':
				edge = (parent[0], n[0])
				self.classifyEdge(edge, cls)

			if self.recentsize[top] == 1 and top.data[0][1] != '0' and top.data[1][1] != '0':
				edge = (top.data[0][0], top.data[1][0])
				self.classifyEdge(edge, cls)

			# Only classify "original" nodes		
			if n[1] == '0':
				self.classifyNode(n[0], cls)				


	def process(self):
		self.high = {}
		self.lists = {}
		self.brackets = {}
		self.recentsize = {}
		self.recentclass = {}
		self.NQClass = {}
		self.currentclass = 0

		self.CEClass = {}
		
		self.queue.reverse() # HACK?

		for n in self.queue:
			self.classifyEdges(n)			
			bl = self.makeBracketList(n)
			assert isinstance(bl, bracket.BracketList)
			self.classifyBracket(n, bl)

	def dump(self, din):
		eq = collections.defaultdict(set)

		for e, cls in din.iteritems():
			eq[cls].add(e)

		d = eq

		keys = d.keys()
		keys.sort()

		minimum = 1

		for k in keys:
			if len(d[k]) >= minimum:
				print k
				for e in d[k]:
					print '\t',e
			
