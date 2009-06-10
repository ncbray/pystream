import sys

class CachedSetManager(object):
	def __init__(self):
		self.cache = {}
		emptyset = frozenset()
		self._emptyset = self.cache.setdefault(emptyset, emptyset)

	def empty(self):
		return self._emptyset

	def inplaceUnion(self, a, b):
		c = a.union(b)
		return self.cache.setdefault(c, c)

	def diff(self, a, b):
		return a-b

	def iter(self, s):
		return iter(s)

	def memory(self):
		mem = sys.getsizeof(self.cache)
		for s1, s2 in self.cache.iteritems():
			mem += sys.getsizeof(s1)
		return mem
