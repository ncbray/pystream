class Condition(object):
	__slots__ = 'value', 'uid', 'size', 'mask'
	def __init__(self, value, uid, size):
		self.value = value
		self.uid   = uid
		self.size  = size

	def __repr__(self):
		return 'cond(%d)' % self.uid

class TreeNode(object):
	__slots__ = 'cond', 'branches', '_hash'

	def __init__(self, cond, branches):
		assert len(branches) == cond.size, "Expected %d branches, got %d." % (cond.size, len(branches))
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

		self.cache      = {}

	def condition(self, value, size):
		if value not in self.conditions:
			cond = Condition(value, len(self.conditions), size)

			# Helper nodes
			cond.mask = [self._tree(cond, tuple(j==i for j in range(size))) for i in range(size)]

			self.conditions[value] = cond
		else:
			cond = self.conditions[value]
			assert cond.size == size
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


	def _ite(self, f, a, b):
		fuid = self.uid(f)
		auid = self.uid(a)
		buid = self.uid(b)

		# If f is a constant, pick either a or b.
		if fuid == -1:
			if f:
				return a
			else:
				return b

		# If a and b are equal, f does not matter.
		if auid == -1 and buid == -1:
			# HACK leaves may not be canonical.
			if a == b:
				return a
		else:
			if a is b:
				return a

		# Check the cache.
		key = (f, a, b)
		if key in self.cache:
			return self.cache[key]

		# Because we know f is not a terminal node, at least f will have branches.
		if fuid > auid:
			maxid   = fuid
			maxnode = f
		else:
			maxid   = auid
			maxnode = a

		if buid > maxid:
			maxid   = buid
			maxnode = b

		# Iterate over the branches for all nodes that have uid == maxid
		nodes = ((f, fuid), (a, auid), (b, buid))
		iterator = zip(*[node.branches if uid == maxid else [node]*len(maxnode.branches) for node, uid in nodes])
		computed = tuple([self._ite(*args) for args in iterator])

		result = self._tree(maxnode.cond, computed)

		self.cache[key] = result
		return result

	def ite(self, f, a, b):
		result = self._ite(f, a, b)
		self.cache.clear()
		return result

	def _restrict(self, a, d, bound):
		uid = self.uid(a)
		if uid < bound:
			# Early out.
			# Should also take care of leaf cases.
			return a

		# Have we seen it before?
		if a in self.cache:
			return self.cache[a]

		if a.cond in d:
			# Restrict this condition.
			result = self._restrict(a.branches[d[a.cond]], d, bound)
		else:
			# No restriction, keep the node.
			branches = tuple([self._restrict(branch, d, bound) for branch in a.branches])
			result = self._tree(a.cond, branches)

		self.cache[a] = result
		return result


	def restrict(self, a, d):
		# Empty restriction -> no change
		if not d: return a

		for cond, index in d.iteritems():
			assert 0 <= index < cond.size, "Invalid restriction"

		bound = max(cond.uid for cond in d.iterkeys())

		result = self._restrict(a, d, bound)
		self.cache.clear()
		return result


	def _simplify(self, domain, tree, default):
		if domain is False:
			return default
		elif domain is True:
			return tree

		duid = self.uid(domain)
		tuid = self.uid(tree)

		if tuid == -1:
			# Tree leaf, domain is not completely false.
			return tree

		key = (domain, tree)
		if key in self.cache:
			return self.cache[key]

		if duid < tuid:
			branches = tuple([self._simplify(domain, branch, default) for branch in tree.branches])
			result   = self._tree(tree.cond, branches)
		else:
			if tuid == duid:
				treeiter = tree.branches
			else:
				treeiter = (tree,)*domain.cond.size

			interesting = set()
			newbranches = []
			for domainbranch, treebranch in zip(domain.branches, treeiter):
				newbranches.append(self._simplify(domainbranch, treebranch, default))
				if domainbranch is not False:
					interesting.add(domainbranch)

			if len(interesting) == 1:
				result = interesting.pop()
			else:
				result = self._tree(domain.cond, tuple(newbranches))

		self.cache[key] = result
		return result

	# Simplify discards information where the domain is False.
	# Unlike ROBDD simplificaiton, tree simplification may discard only some
	# of the branches in the node.  If the remaining (simplified) branches
	# are not the same, the discarded branches are replaced with the default value.
	# ROBDD simplificaiton does not need a default values, as if there are only two branches,
	# discarding one will eliminate the node.
	# TODO in the case there domain > tree, it might be possible to get better results
	# where default comes into play?
	def simplify(self, domain, tree, default):
		result = self._simplify(domain, tree, default)
		self.cache.clear()
		return result