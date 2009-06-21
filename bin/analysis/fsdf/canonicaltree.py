import itertools

class Condition(object):
	__slots__ = 'value', 'uid', 'size', 'mask'
	def __init__(self, value, uid, size):
		self.value = value
		self.uid   = uid
		self.size  = size

	def __repr__(self):
		return 'cond(%d)' % self.uid

	def __eq__(self, other):
		return self is other

	def __lt__(self, other):
		return self.uid < other.uid

	def __le__(self, other):
		return self.uid <= other.uid

	def __gt__(self, other):
		return self.uid > other.uid

	def __ge__(self, other):
		return self.uid >= other.uid

class ConditionManager(object):
	def __init__(self):
		self.conditions = {}

	def condition(self, value, size):
		if value not in self.conditions:
			cond = Condition(value, len(self.conditions), size)

			# Helper nodes
			cond.mask = [self.boolManager.tree(cond, tuple(self.boolManager.leaf(j==i) for j in range(size))) for i in range(size)]

			self.conditions[value] = cond
		else:
			cond = self.conditions[value]
			assert cond.size == size
		return cond


class AbstractNode(object):
	__slots__ = '_hash'

	def __hash__(self):
		return self._hash

	def leaf(self):
		return False

	def tree(self):
		return False


class LeafNode(AbstractNode):
	cond = Condition(None, -1, 0)

	__slots__ = 'value'
	def __init__(self, value):
		self.value = value
		self._hash = hash(value)

	def __eq__(self, other):
		return self is other or (type(self) == type(other) and self.value == other.value)

	def __repr__(self):
		return 'leaf(%r)' % (self.value)

	def iter(self, cond):
		return (self,)*cond.size

	def leaf(self):
		return True

class TreeNode(AbstractNode):
	__slots__ = 'cond', 'branches'

	def __init__(self, cond, branches):
		assert len(branches) == cond.size, "Expected %d branches, got %d." % (cond.size, len(branches))
		self.cond     = cond
		self.branches = branches
		self._hash    = hash((cond, branches))

	def __eq__(self, other):
		return self is other or (type(self) == type(other) and self.cond == other.cond and self.branches == other.branches)

	def __repr__(self):
		return 'tree<%d>%r' % (self.cond.uid, self.branches)

	def iter(self, cond):
		if self.cond is cond:
			return self.branches
		else:
			return (self,)*cond.size

	def branch(self, index):
		return self.branches[index]

	def tree(self):
		return True

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

		assert identity is noValue or isinstance(identity, LeafNode)
		assert leftIdentity is noValue or isinstance(leftIdentity, LeafNode)
		assert rightIdentity is noValue or isinstance(rightIdentity, LeafNode)

		assert null is noValue or isinstance(null, LeafNode)
		assert leftNull is noValue or isinstance(leftNull, LeafNode)
		assert rightNull is noValue or isinstance(rightNull, LeafNode)


		self.manager    = manager
		self.func       = func
		self.symmetric  = symmetric
		self.stationary = stationary

		if symmetric or identity is not noValue:
			assert leftIdentity  is noValue
			assert rightIdentity is noValue

			self.leftIdentity  = identity
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
		if self.stationary and a is b:
			# f(a, a) = a
			return a

		maxcond = max(a.cond, b.cond)

		if maxcond.uid == -1:
			# leaf/leaf computation
			result = self.manager.leaf(self.func(a.value, b.value))
		else:
			branches = tuple([self._apply(*branches) for branches in itertools.izip(a.iter(maxcond), b.iter(maxcond))])
			result = self.manager.tree(maxcond, branches)
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
		if a is self.leftIdentity:
			result = b
		elif a is self.leftNull:
			result = self.leftNull
		elif b is self.rightIdentity:
			result = a
		elif b is self.rightNull:
			result = self.rightNull
		else:
			# Cache miss, no identities, must compute
			result = self.compute(a, b)

		return self.cache.setdefault(key, result)

	def __call__(self, a, b):
		self.cacheHit  = 0
		self.cacheMiss = 0
		result = self._apply(a, b)
		#print "%d/%d" % (self.cacheHit, self.cacheHit+self.cacheMiss)
		self.cache.clear() # HACK don't retain cache between computations?
		return result


class CanonicalTreeManager(object):
	def __init__(self, coerce):
		self.coerce = coerce

		self.trees      = {}
		self.leaves     = {}

		self.cache      = {}

	def leaf(self, value):
		value = self.coerce(value)
		if value not in self.leaves:
			result = LeafNode(value)
			self.leaves[value] = result
		else:
			result = self.leaves[value]
		return result

	def tree(self, cond, branches):
		assert isinstance(branches, tuple), type(branches)
		for branch in branches:
			assert isinstance(branch, AbstractNode), branch
			assert cond > branch.cond, (cond.uid, branch.cond.uid, branches)

		first = branches[0]
		for branch in branches:
			if branch is not first:
				break
		else:
			# They're all the same, don't make a tree.
			return first

		tree = TreeNode(cond, branches)
		return self.trees.setdefault(tree, tree)

	def _ite(self, f, a, b):
		# If f is a constant, pick either a or b.
		if f.cond.uid == -1:
			if f.value:
				return a
			else:
				return b

		# If a and b are equal, f does not matter.
		if a is b:
			return a

		# Check the cache.
		key = (f, a, b)
		if key in self.cache:
			return self.cache[key]

		# Iterate over the branches for all nodes that have uid == maxid
		maxcond = max(f.cond, a.cond, b.cond)
		iterator = itertools.izip(f.iter(maxcond), a.iter(maxcond), b.iter(maxcond))
		computed = tuple([self._ite(*args) for args in iterator])
		result = self.tree(maxcond, computed)

		self.cache[key] = result
		return result

	def ite(self, f, a, b):
		result = self._ite(f, a, b)
		self.cache.clear()
		return result

	def _restrict(self, a, d, bound):
		if a.cond < bound:
			# Early out.
			# Should also take care of leaf cases.
			return a

		# Have we seen it before?
		if a in self.cache:
			return self.cache[a]

		index = d.get(a.cond)
		if index is not None:
			# Restrict this condition.
			result = self._restrict(a.branch(index), d, bound)
		else:
			# No restriction, keep the node.
			branches = tuple([self._restrict(branch, d, bound) for branch in a.branches])
			result = self.tree(a.cond, branches)

		self.cache[a] = result
		return result


	def restrict(self, a, d):
		# Empty restriction -> no change
		if not d: return a

		for cond, index in d.iteritems():
			assert 0 <= index < cond.size, "Invalid restriction"

		bound = min(d.iterkeys())

		result = self._restrict(a, d, bound)
		self.cache.clear()
		return result


	def _simplify(self, domain, tree, default):
		# If the domain is constant, select between the tree and the default.
		if domain.leaf():
			if domain.value:
				return tree
			else:
				return default

		if tree.leaf():
			# Tree leaf, domain is not completely false.
			return tree

		key = (domain, tree)
		if key in self.cache:
			return self.cache[key]

		if domain.cond < tree.cond:
			branches = tuple([self._simplify(domain, branch, default) for branch in tree.branches])
			result   = self.tree(tree.cond, branches)
		else:
			treeiter = tree.iter(domain.cond)

			interesting = set()
			newbranches = []
			for domainbranch, treebranch in itertools.izip(domain.branches, treeiter):
				newbranches.append(self._simplify(domainbranch, treebranch, default))
				if not domainbranch.leaf() or domainbranch.value:
					interesting.add(treebranch)

			if len(interesting) == 1:
				result = interesting.pop()
			else:
				result = self.tree(domain.cond, tuple(newbranches))

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


def BoolManager(conditions):
	manager = CanonicalTreeManager(bool)
	conditions.boolManager = manager

	manager.true  = manager.leaf(True)
	manager.false = manager.leaf(False)

	manager.and_ = BinaryTreeFunction(manager, lambda l, r: l & r,
		symmetric=True, stationary=True, identity=manager.true, null=manager.false)
	manager.or_  = BinaryTreeFunction(manager, lambda l, r: l | r,
		symmetric=True, stationary=True, identity=manager.false, null=manager.true)

	return manager

def SetManager():
	manager = CanonicalTreeManager(frozenset)

	manager.empty = manager.leaf(frozenset())

	manager.intersect = BinaryTreeFunction(manager, lambda l, r: l & r,
		symmetric=True, stationary=True, null=manager.empty)
	manager.union = BinaryTreeFunction(manager, lambda l, r: l | r,
		symmetric=True, stationary=True, identity=manager.empty)

	return manager