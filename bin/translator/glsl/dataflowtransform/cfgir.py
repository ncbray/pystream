class CFGNode(object):
	__slots__ = 'prev', 'next'

	def addNext(self, other):
		assert self.next is None
		self.next = other._addPrev(self)

	def replaceNext(self, current, replacement):
		assert self.next is current
		self.next = replacement

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

			self.prev.replaceNext(self, merge)
			merge.next = self

			merge._addPrev(self.prev)
			merge._addPrev(other)
			self.prev = merge
			return self.prev

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
		self.next.append(other._addPrev(self))

	def replaceNext(self, current, replacement):
		index = self.next.index(current)
		self.next[current] = replacement


class CFGMerge(CFGNode):
	def __init__(self):
		CFGNode.__init__(self)
		self.prev = []
		self.next = None

	def _addPrev(self, other):
		self.prev.append(other)
		return self