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

class CFGNode(object):
	__slots__ = 'parent', 'prev', 'next'

	def __init__(self):
		self.parent = None

	def addNext(self, other):
		assert self.next is None
		assert other is not None
		other = other._addPrev(self)
		assert other is not None
		self.next = other

	def _addPrev(self, other):
		if self.prev is None:
			# prev is undefined
			self.prev = other
			return self
		elif isinstance(self.prev, CFGMerge):
			# prev is a merge
			self.prev._addPrev(other)
			return self.prev
		else:
			# prev is not a merge, turn it into one.
			merge = CFGMerge()

			oldprev = self.prev
			oldprev.replaceNext(self, merge)
			merge.addNext(self)

			merge._addPrev(other)
			return self.prev

	def removeNext(self, node):
		assert self.next is node
		self.next = None
		node._removePrev(self)

	def _removePrev(self, node):
		assert self.prev is node
		self.prev = None

	def replaceNext(self, node, replacement):
		assert self.next is node
		self.next = replacement

		node._removePrev(self)
		replacement._addPrev(self)

	def iternext(self):
		if self.next is None:
			return ()
		else:
			return (self.next,)

	def iterprev(self):
		if self.prev is None:
			return ()
		else:
			return (self.prev,)

	def numIn(self):
		return 1 if self.prev is not None else 0

	def numOut(self):
		return 1 if self.next is not None else 0

	def isCompound(self):
		return False

	def isLinear(self):
		return True

	def isSuite(self):
		return False

class CFGBlock(CFGNode):
	__slots__ = 'hyperblock', 'predicates', 'ops'

	def __init__(self, hyperblock, predicates):
		CFGNode.__init__(self)
		self.hyperblock = hyperblock
		self.predicates = predicates
		self.ops        = []

		self.prev       = None
		self.next       = None


class CFGBranch(CFGNode):
	__slots__ = 'op'
	def __init__(self, op):
		CFGNode.__init__(self)
		self.op = op

		self.prev = None
		self.next = []

	def addNext(self, other):
		assert other is not None
		other = other._addPrev(self)
		assert other is not None
		self.next.append(other)

	def iternext(self):
		return self.next

	def numOut(self):
		return len(self.next)

	def removeNext(self, node):
		index = self.next.index(node)
		del self.next[index]
		node._removePrev(self)

	def replaceNext(self, node, replacement):
		index = self.next.index(node)
		self.next[index] = replacement

		node._removePrev(self)
		replacement._addPrev(self)

	def isLinear(self):
		return False


class CFGMerge(CFGNode):
	def __init__(self):
		CFGNode.__init__(self)
		self.prev = []
		self.next = None

	def _addPrev(self, other):
		assert other is not None
		self.prev.append(other)
		return self

	def _removePrev(self, node):
		index = self.prev.index(node)
		del self.prev[index]


	def optimize(self):
		if len(self.prev) == 1:
			# Remove degenerate merges.
			prev = self.prev[0]
			next = self.next

			next._removePrev(self)
			prev.replaceNext(self, next)

	def iterprev(self):
		return self.prev

	def isLinear(self):
		return False


######################
### Compound nodes ###
######################

class CFGEntry(CFGNode):
	__slots__ = ()

	def __init__(self):
		CFGNode.__init__(self)
		self.prev = None
		self.next = None

	def _addPrev(self, other):
		raise NotImplementedError

	def _removePrev(self, node):
		raise NotImplementedError


class CFGExit(CFGNode):
	__slots__ = ()

	def __init__(self):
		CFGNode.__init__(self)
		self.prev = None
		self.next = None

	def addNext(self, other):
		raise NotImplementedError

	def removeNext(self, node):
		raise NotImplementedError

	def replaceNext(self, node):
		raise NotImplementedError


class CFGCompoundNode(CFGNode):
	__slots__ = 'entry', 'exit'

	def __init__(self):
		CFGNode.__init__(self)

		self.entry = CFGEntry()
		self.entry.parent = self

		self.exit = CFGExit()
		self.exit.parent = self

	def isCompound(self):
		return True


class CFGSuite(CFGCompoundNode):
	__slots__ = 'nodes'
	def __init__(self, node):
		CFGCompoundNode.__init__(self)

		self.prev = None
		self.next = None


		assert node.isLinear()

		if node.prev:
			prev = node.prev
			prev.replaceNext(node, self)

		self.entry.addNext(node)

		if node.next:
			next = node.next
			node.replaceNext(next, self.exit)
			self.addNext(next)

		node.parent = self
		self.nodes = [node]

	def insertHead(self, node):
		assert node.isLinear()

		# Orphan the node.

		assert node.next is self
		assert self.prev is node

		node.removeNext(self)

		# Redirect the entry
		if node.prev:
			prev = node.prev
			prev.replaceNext(node, self)

			assert self.prev is prev
			assert node.prev is None

		# node should now be an orphan

		# Insert at the begining.
		first = self.entry.next
		self.entry.replaceNext(first, node)
		node.addNext(first)

		node.parent = self
		self.nodes.insert(0, node)

	def isSuite(self):
		return True


class CFGTypeSwitch(CFGCompoundNode):
	__slots__ = 'switch', 'cases', 'merge'

	def __init__(self, switch, cases, merge):
		CFGCompoundNode.__init__(self)

		self.switch = switch
		self.cases  = cases
		self.merge  = merge

		self.prev = None
		self.next = None

		# Modify the graph
		if switch.prev: switch.prev.replaceNext(switch, self)
		self.entry.addNext(switch)
		merge.addNext(self.exit)

		# Set the parrent points
		self.switch.parent = self
		for case in self.cases:
			case.parent = self
		self.merge.parent = self
