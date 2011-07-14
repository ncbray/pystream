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
