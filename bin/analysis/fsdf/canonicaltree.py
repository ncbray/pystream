class Condition(object):
	__slots__ = 'value', 'uid'
	def __init__(self, value, uid):
		self.value = value
		self.uid   = uid

	def __repr__(self):
		return 'cond(%d)' % self.uid

class TreeNode(object):
	__slots__ = 'cond', 'branches', '_hash'

	def __init__(self, cond, branches):
		self.cond     = cond
		self.branches = branches
		self._hash    = hash((cond, branches))

	def __hash__(self):
		return self._hash

	def __eq__(self, other):
		return self is other or (type(self) == type(other) and self.cond == other.cond and self.branches == other.branches)

	def __repr__(self):
		return 'tree<%d>%r' % (self.cond.uid, self.branches)

class NoValue(object):
	__slots__ = ()
noValue = NoValue()

class BinaryTreeFunction(object):
	__slots__ = ['manager', 'func', 'symmetric', 'stationary',
			'leftIdentity', 'rightIdentity',
			'leftNull', 'rightNull',
			'cache', 'cacheHit', 'cacheMiss']

	def __init__(self, manager, func, symmetric=False, stationary=False,
			identity=noValue, leftIdentity=noValue, rightIdentity=noValue,
			null=noValue, leftNull=noValue, rightNull=noValue):

		self.manager    = manager
		self.func       = func
		self.symmetric  = symmetric
		self.stationary = stationary

		if symmetric or identity is not noValue:
			assert leftIdentity  is noValue
			assert rightIdentity is noValue

			self.leftIdentity = identity
			self.rightIdentity = identity
		else:
			self.leftIdentity  = leftIdentity
			self.rightIdentity = rightIdentity

		if symmetric or null is not noValue:
			assert leftNull is noValue
			assert rightNull is noValue

			self.leftNull  = null
			self.rightNull = null
		else:
			self.leftNull  = leftNull
			self.rightNull = rightNull

		self.cache     = {}

	def compute(self, a, b):
		auid = self.manager.uid(a)
		buid = self.manager.uid(b)

		if auid == -1 and buid == -1:
			# leaf/leaf computation
			result = self.func(a, b)
		else:
			if auid == buid:
				# branch/branch computation
				if self.stationary and a is b:
					# f(a, a) = a
					return a

				# Branches equal, split both.
				cond = a.cond
				branches = tuple([self._apply(abranch, bbranch) for abranch, bbranch in zip(a.branches, b.branches)])
			elif auid < buid:
				# Split b.
				cond = b.cond
				branches = tuple([self._apply(a, branch) for branch in b.branches])
			else:
				# Split a.
				cond = a.cond
				branches = tuple([self._apply(branch, b) for branch in a.branches])
			result = self.manager._tree(cond, branches)

		return result

	def _apply(self, a, b):
		# See if we've alread computed this.
		key = (a, b)
		if key in self.cache:
			self.cacheHit += 1
			return self.cache[key]
		else:
			if self.symmetric:
				# If the function is symetric, try swaping the arguments.
				altkey = (b, a)
				if altkey in self.cache:
					self.cacheHit += 1
					return self.cache[altkey]

			self.cacheMiss += 1

		# Use identities to bypass computation.
		# This is not very helpful for leaf / leaf pairs, but provides
		# an earily out for branch / leaf pairs.
		if self.leftIdentity is not noValue and a == self.leftIdentity:
			result = b
		elif self.leftNull is not noValue and a == self.leftNull:
			result = self.leftNull
		elif self.rightIdentity is not noValue and b == self.rightIdentity:
			result = a
		elif self.rightNull is not noValue and b == self.rightNull:
			result = self.rightNull
		else:
			# Cache miss, no identities, must compute
			result = self.compute(a, b)

		return self.cache.setdefault(key, result)

	def apply(self, a, b):
		self.cacheHit  = 0
		self.cacheMiss = 0
		result = self._apply(a, b)
		#print "%d/%d" % (self.cacheHit, self.cacheHit+self.cacheMiss)
		self.cache.clear() # HACK don't retain cache between computations?
		return result


class CanonicalTreeManager(object):
	def __init__(self):
		self.conditions = {}
		self.trees      = {}

	def condition(self, value):
		if value not in self.conditions:
			cond = Condition(value, len(self.conditions))
			self.conditions[value] = cond
		else:
			cond = self.conditions[value]
		return cond

	def tree(self, cond, branches):
		return self._tree(cond, branches)

	def _tree(self, cond, branches):
		assert isinstance(branches, tuple), type(branches)
		for branch in branches:
			assert cond.uid > self.uid(branch)

		first = branches[0]
		for branch in branches:
			if branch != first:
				break
		else:
			# They're all the same, don't make a tree.
			return first

		tree = TreeNode(cond, branches)
		return self.trees.setdefault(tree, tree)

	def uid(self, node):
		if isinstance(node, TreeNode):
			return node.cond.uid
		else:
			return -1