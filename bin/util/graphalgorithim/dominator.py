# Copyright 2011 Nicholas Bray
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from . import basic

class ReversePostorderCrawler(object):
	def __init__(self, G, head):
		self.G = G
		self.head = head

		self.all = set(G.iterkeys())

		self.processed = set((self.head,))
		self.order = []

		for nextNode in self.G[self.head]:
			self(nextNode)

		# Look for inaccessible cycles
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
			_parent,children = stack[-1]
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

	# Find the predecessors, in reverse postorder space.
	pred = {}
	for node, nexts in G.iteritems():
		i = forward[node]
		for nextNode in nexts:
			n = forward[nextNode]

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

	# Calculate a fixed point solution
	changed = True
	while changed:
		changed = False
		for node in range(1, count):
			# Find an initial value for the immediate dominator
			if doms[node] is None:
				new_idom = min(pred[node])
				assert new_idom < node
			else:
				new_idom = doms[node]

			# Refine the immediate dominator,
			# make it consistent with the predecessors.
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
	for node, idom in enumerate(doms):
		if node is 0: continue # Skip the head
		node = reverse[node]
		idom = reverse[idom]
		idoms[node] = idom

	return treeFromIDoms(idoms), idoms



def makeSingleHead(G, head):
	entryPoints = basic.findEntryPoints(G)
	G[head] = entryPoints



class DomInfo(object):
	__slots__ = 'pre', 'post', 'prev'

	def __init__(self):
		self.pre  = 0
		self.post = 0
		self.prev = []

	# For self to dominate other, it is necessary (but not sufficient)
	# that pre and post bracket other's pre and post
	def cannotDominate(self, other):
		return self.pre > other.pre or self.post < other.post

class IDomFinder(object):
	def __init__(self, forwardCallback):
		self.pre  = {}
		self.domInfo = {}
		self.uid  = 0
		self.order = []
		self.forwardCallback = forwardCallback

	def process(self, node):
		if node not in self.domInfo:
			info = DomInfo()
			self.domInfo[node] = info
			info.pre = self.uid
			self.uid += 1

			for child in self.forwardCallback(node):
				childInfo = self.process(child)
				childInfo.prev.append(node)

			info.post = self.uid
			self.uid += 1

			self.order.append(node)

			return info
		else:
			return self.domInfo[node]

	def findCompatable(self, current, other):
		if current is None or other is None:
			return None

		cinfo = self.domInfo[current]
		oinfo = self.domInfo[other]

		while cinfo.cannotDominate(oinfo):
			current = self.idom[current]
			if current is None:
				return None
			cinfo   = self.domInfo[current]

		return current

	def findIDoms(self):
		self.idom = {}

		for node in reversed(self.order):
			nodeInfo = self.domInfo[node]

			n = len(nodeInfo.prev)

			if n == 0:
				# No previous nodes, idom is ill defined
				best = None
			elif n == 1:
				# One previous node, trivial dominator
				best = nodeInfo.prev[0]
			else:
				# Look for the parent with the biggest post order
				# This may not be the idom, but is is the most likely
				# Further, it will have already been processed
				# (assuming all nodes are accessible from the root)
				# Further, it will NOT be a back edge

				# Choose the first one to start
				prevs = nodeInfo.prev
				best  = prevs[0]
				binfo = self.domInfo[best]

				# TODO redundant computation of node.prev[0]
				for prev in prevs:
					pinfo = self.domInfo[prev]
					if pinfo.post > binfo.post:
						best  = prev
						binfo = binfo

				# Find the closest node that dominates all of parents (or is one)
				# At worst, this will perform a linear search up to the entry.
				# Merges, however, will skip to their idom
				for prev in prevs:
					best = self.findCompatable(best, prev)

			self.idom[node] = best

		return self.idom

def findIDoms(roots, forwardCallback):
	idf = IDomFinder(forwardCallback)
	for root in roots:
		idf.process(root)
	return idf.findIDoms()

def treeFromIDoms(idoms):
	tree = {}

	for node, idom in idoms.iteritems():
		if idom not in tree:
			tree[idom] = [node]
		else:
			tree[idom].append(node)

	return tree
