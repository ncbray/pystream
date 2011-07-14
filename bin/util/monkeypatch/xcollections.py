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

from weakref import ref
from collections import *
from . xnamedtuple import namedtuple

class lazydict(defaultdict):
	__slots__ = ()
	def __missing__(self, key):
		result = self.default_factory(key)
		self[key] = result
		return result

class weakcache(object):
	__slots__ = 'data', '_remove', '__weakref__'

	def __init__(self, dict=None):
		self.data = {}

		def remove(wr, weakself=ref(self)):
			self = weakself()

			if self is not None:
				del self.data[wr]

		self._remove = remove

	def __getitem__(self, key):
		wr = ref(key, self._remove)

		if wr in self.data:
			result = self.data[wr]()
		else:
			result = None

		if result is None:
			self.data[wr] = wr
			result = key

		return result

	def __delitem__(self, key):
		del self.data[ref(key)]

	def __contains__(self, key):
		try:
			wr = ref(key)
		except TypeError:
			return False
		return wr in self.data

	def __iter__(self):
		for wr in self.data.iterkeys():
			obj = wr()
			if obj is not None:
				yield obj

	def __len__(self):
		return len(self.data)
