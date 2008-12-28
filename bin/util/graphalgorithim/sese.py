from __future__ import absolute_import

import PADS.DFS
import collections


class StartNode(object):
	__slots__ = ()

startNode = StartNode()

class EndNode(object):
	__slots__ = ()

endNode = EndNode()

class Bracket(object):
	def __init__(self, data):
		self.data = data
		self.prev = None
		self.next = None

	def delete(self):
		assert not self.isOrphaned()

		
		self.prev.next = self.next
		self.next.prev = self.prev

		self.prev = None
		self.next = None

	def insertAfter(self, other):
		assert other.isOrphaned()
		
		other.prev = self
		other.next = self.next

		self.next.prev = other
		self.next = other


	def isOrphaned(self):
		return self.prev == None and self.next == None

	def __repr__(self):
		return "Bracket(%s)" % repr(self.data)

class BracketList(object):
	def __init__(self):
		self.root = Bracket(None)
		self.root.next = self.root
		self.root.prev = self.root
		self.__size = 0

	def size(self):
		return self.__size

	def push(self, bracket):
		self.root.insertAfter(bracket)
		self.__size += 1

	def top(self):
		return self.root.next

	def delete(self, bracket):
		bracket.delete()
		self.__size -= 1

	def forwards(self):
		current = self.root.next
		while current != self.root:
			yield current
			current = current.next

	def backwards(self):
		current = self.root.prev
		while current != self.root:
			yield current
			current = current.prev

	def concat(self, other):
		# Join the lists
		self.root.prev.next = other.root.next
		other.root.next.prev = self.root.prev

		# Connect the end of the new list too the root.
		self.root.prev = other.root.prev
		other.root.prev.next = self.root

		self.__size += other.__size

		# Reset the other root.
		other.root.next = other.root
		other.root.prev = other.root
		other.__size = 0

class Searcher(object):
	def search(self, G, start):
		"""Perform a depth first search of graph G."""
		dispatch = [self.backedge,self.preorder,self.postorder]
		for v,w,edgetype in PADS.DFS.search(G, start):
			dispatch[edgetype](v,w)

	def preorder(self,parent,child):
		pass

	def postorder(self,parent,child):
		pass

	def backedge(self,source,destination):
		pass

class CycleEquivilenceSearcher(Searcher):
	def __init__(self,G, head, tail):

		self.head = head
		self.tail = tail
		
		self.originalStart = 'start'
		self.originalG = G
		
		# Expand G
		G, start = orderedUndirected(G, self.originalStart)
		
		self.G = G

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

	def preorder(self,parent,child):
		assert not child in self.number
		self.number[child] = self.current
		self.node[self.current] = child
		self.current += 1

		self.queue.append(child)
		self.markEdge(parent, child, True)

	def postorder(self,parent,child):
		pass

	def backedge(self,source,destination):
		self.markEdge(source, destination, False)

	

	def classifyEdges(self, n):
		nnum = self.number[n]
		for child in self.G[n]:
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
			self.brackets[index] = Bracket(index)
		return self.brackets[index]

	def makeBracketList(self, n):
		bl = BracketList()
		self.lists[n] = bl

		# Gather child bracket lists
		for child in self.child[n]:
			cbl = self.lists[child]
			bl.concat(cbl)

		# Remove previous backedges.
		for d in self.backto[n]:
			bracket = self.bracket(d, n)
			bl.delete(bracket)

		for d in self.capping[n]:
			bracket = self.bracket(d, n)
			bl.delete(bracket)

		# Add eminating backedges
		for a in self.backfrom[n]:
			bracket = self.bracket(n, a)
			bl.push(bracket)
			self.recentsize[bracket] = -1

		cap = self.findCap(n)

		# Add a capping back edge
		if len(self.child[n]) > 1:
			assert cap != None
			bracket = self.bracket(n, cap)
			bl.push(bracket)				
			self.recentsize[bracket] = -1
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
			assert isinstance(bl, BracketList)
			self.classifyBracket(n, bl)

		#self.dump(self.CEClass)
		#self.dump(self.NQClass)

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
			


# Explicitly expands the graph so each node consists of an "in", "internal", and "out" node.
# Also creates directed "back" edges, which guarentees the search will find all nodes.
def orderedUndirected(G, start):
	reverse = collections.defaultdict(set)
	for n1, v in G.iteritems():
		for n2 in v:
			if not n1 in G[n2]:
				reverse[n2].add(n1)

	nG = {}
	if False:
		for n1, v in G.iteritems():
			# Forward edges before reverse edges.
			nG[n1] = tuple(v)+tuple(reverse[n1].difference(v))
	else:
		# TODO don't explictly expand graph?
		for n1, v in G.iteritems():
			# Forward edges before reverse edges.
			nG[(n1, 'in')] = ((n1, '0'),)+tuple([(n, 'out') for n in reverse[n1]])
			nG[(n1, '0')] = ((n1, 'out'), (n1, 'in'))
			nG[(n1, 'out')] = tuple([(n, 'in') for n in v])+((n1, '0'),)

		start = (start, 'out')

	return nG, start

class Sentinel(object):
	__slots__ = ()


class SESERegion(object):
	def __init__(self, entry, exit):
		self.entry    = entry
		self.exit     = exit
		self.parent   = None
		self.children = []
		self.nodes    = []
		self.edges    = []
		
	def addChild(self, node):
		assert not node.parent
		node.parent = self
		self.children.append(node)

	def addEdge(self, src, dst):
		self.edges.append((src, dst))

	def __repr__(self):
		return "SESERegion(%s, %s)" % (repr(self.entry), repr(self.exit))

	def dump(self, indent=''):
		print indent, repr(self)
		for child in self.children:
			child.dump(indent+'\t')

		for node in self.nodes:
			print indent+'\t', node

		for src, dst in self.edges:
			print indent+'\t', src, '->', dst
			

class FindRegions(Searcher):
	def __init__(self, G, head, tail, nodeClass, edgeClass):
		#assert len(G[start]) == 1
		
		self.G = G
		self.head = head
		self.tail = tail

		self.dummyHead = Sentinel()
		self.dummyTail = Sentinel()
		
		
		self.start = 'start'
		self.nodeClass = nodeClass
		self.edgeClass = edgeClass

		self.lastEdge = {}

		self.entryRegion = {}
		self.exitRegion  = {}

		# Builds the regions
		self.search(G, self.start)

		self.depth = {}

	def handleEdge(self, edge):
		if edge in self.edgeClass and edge[1] != self.start:
			cls = self.edgeClass[edge]

			if cls in self.lastEdge:
				edgein = self.lastEdge[cls]
				edgeout = edge
				r = SESERegion(edgein[1], edgeout[0])
				self.entryRegion[edgein] = r
				self.exitRegion[edgeout] = r
##				
##				print "REGION", edge, r
##			else:
##				print "INIT", edge

			self.lastEdge[cls] = edge
		else:
			pass #print "BACK", edge

	def preorder(self, parent, child):
		if parent != child:
			edge = (parent, child)
			self.handleEdge(edge)
	
	def backedge(self, source, dest):
		self.handleEdge((source, dest))

	def process(self):
		# Figures out the contexts/hierarchy of the regions.
		self.processed = set()


		top = SESERegion('start', 'end')
		self.depth[top] = 0

		self.visit(self.start, top)

		assert len(top.children) == 1
		return top.children[0]
		#return top
		
	def visit(self, node, region):
		assert region
		if not node in self.processed:
			self.processed.add(node)
			region.nodes.append(node)

			for next in self.G[node]:
				self.processEdge(node, next, region)

	def processEdge(self, node, next, region):
		edge = (node, next)

		# r1 is the region exited
		# r2 is the region entered
		# Either region will be None if they are the same as "region"
		# Internal edges will be None/None

		r1 = self.exitRegion.get(edge)
		r2 = self.entryRegion.get(edge)


##		print
##		print "Edge", edge
##		print '\t', region
##		print '\t', r1
##		print '\t', r2
		
		rn = region
		
		if region == r1 or region == r2:
##			print "BACK", region, r1, r2
			assert region.parent, (node, region)
			rn = region.parent

		# May be parented to the current region, or the parrent region.
		if r1 is not None and r1 != region:
			assert not r1 in self.depth
			assert rn in self.depth
			self.depth[r1] = self.depth[rn]+1

##			print "Contains", rn, "<-", r1, self.depth[r1]
			rn.addChild(r1)
			rn = r1


		# May be parented to the current region, or the parrent region.					
		if r2 is not None and r2 != region:
			assert not r2 in self.depth
			assert rn in self.depth
			self.depth[r2] = self.depth[rn]+1

##			print "Contains", rn, "<-", r2, self.depth[r2]
			rn.addChild(r2)
			rn = r2

		# rn is not the region of the "next" node.

		n1 = node
		r1 = region
		
		n2 = next
		r2 = rn

		self.addEdge(n1, r1, n2, r2)

		self.visit(next, rn)

	def addEdge(self, n1, r1, n2, r2):
		# Even up the depths.
		while self.depth[r1] > self.depth[r2]:
			n1, r1 = r1, r1.parent
		while self.depth[r1] < self.depth[r2]:
			n2, r2 = r2, r2.parent

		self.__addEdge(n1, r1, n2, r2)

	def __addEdge(self, n1, r1, n2, r2):
		if r1 is not r2:
			self.__addEdge(r1, r1.parent, r2, r2.parent)
		else:
			r1.addEdge(n1, n2)



def findCycleEquivilences(G, head, tail):
	start = 'start'
	
	s = CycleEquivilenceSearcher(G, head, tail)
	nodeClass, edgeClass = s.NQClass, s.CEClass

	fr = FindRegions(G, head, tail, nodeClass, edgeClass)
	pst = fr.process()

	print "========"
	pst.dump()

	return pst
