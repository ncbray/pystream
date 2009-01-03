from __future__ import absolute_import

import PADS.DFS

from . import cycleequivilence

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
		return "SESERegion(%r, %r)" % (self.entry, self.exit)

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

		assert len(top.children) > 0

		if len(top.children) == 1:
			return top.children[0]
		else:
			# HACK
			return top
		
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
	
	s = cycleequivilence.CycleEquivilenceSearcher(G, head, tail)
	nodeClass, edgeClass = s.NQClass, s.CEClass

	fr = FindRegions(G, head, tail, nodeClass, edgeClass)
	pst = fr.process()

	return pst
