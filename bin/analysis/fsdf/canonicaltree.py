class Condition(object):
	__slots__ = 'value', 'uid'
	def __init__(self, value, uid):
		self.value = value
		self.uid   = uid

class TreeNode(object):
	__slots__ = 'cond', 't', 'f', '_hash'

	def __init__(self, cond, t, f):
		self.cond  = cond
		self.t     = t
		self.f     = f
		self._hash = hash((cond, t, f))

	def __hash__(self):
		return self._hash

	def __eq__(self, other):
		return self is other or (type(self) == type(other) and self.cond == other.cond and self.t == other.t and self.f == other.f)

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

	def tree(self, cond, t, f):
		return self._tree(cond, t, f)

	def _tree(self, cond, t, f):
		assert cond.uid > self.uid(t)
		assert cond.uid > self.uid(f)

		if t == f:
			return t
		else:
			tree = TreeNode(cond, t, f)
			return self.trees.setdefault(tree, tree)

	def uid(self, node):
		if isinstance(node, TreeNode):
			return node.cond.uid
		else:
			return -1

	def _apply(self, func, a, b, cache):
		key = (a, b)
		if key in cache:
			return cache[key]

		auid = self.uid(a)
		buid = self.uid(b)

		if auid == -1 and buid == -1:
			result = func(a, b)
		elif auid == buid:
			result = self._tree(a.cond, self._apply(func, a.t, b.t, cache), self._apply(func, a.f, b.f, cache))
		elif auid < buid:
			result = self._tree(b.cond, self._apply(func, a, b.t, cache), self._apply(func, a, b.f, cache))
		else:
			result = self._tree(a.cond, self._apply(func, a.t, b, cache), self._apply(func, a.f, b, cache))

		return cache.setdefault(key, result)

	def apply(self, func, a, b):
		return self._apply(func, a, b, {})