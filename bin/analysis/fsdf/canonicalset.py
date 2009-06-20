import sys

class CanonicalSetManager(object):
	def __init__(self):
		self.cache = {}
		emptyset = frozenset()
		self._emptyset = self.cache.setdefault(emptyset, emptyset)

	def empty(self):
		return self._emptyset

	def canonical(self, iterable):
		s = frozenset(iterable)
		return self.cache.setdefault(s, s)

	def _canonical(self, s):
		return self.cache.setdefault(s, s)

	def inplaceUnion(self, a, b):
		return self._canonical(a.union(b))

	def union(self, a, b):
		return self._canonical(a.union(b))

	def intersection(self, a, b):
		return self._canonical(a.intersection(b))

	def uncachedDiff(self, a, b):
		return a-b

	def iter(self, s):
		return iter(s)

	def memory(self):
		mem = sys.getsizeof(self.cache)
		for s in self.cache.iterkeys():
			mem += sys.getsizeof(s)
		return mem
