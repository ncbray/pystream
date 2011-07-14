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

from util.monkeypatch import xcollections

class Sentinel(object):
	__slots__ = 'name', '__weakref__'

	def __init__(self, name):
		self.name = name

	def __repr__(self):
		return self.name


# An object that is equivalent if its "canonical values" are equivalent.
class CanonicalObject(object):
	__slots__ = 'canonical', 'hash', '__weakref__'

	def __init__(self, *args):
		self.setCanonical(*args)

	def setCanonical(self, *args):
		self.canonical = args
		self.hash = id(type(self))^hash(args)

	def __hash__(self):
		return self.hash

	def __eq__(self, other):
		return type(self) == type(other) and self.canonical == other.canonical

	def __repr__(self):
		canonicalStr = ", ".join([repr(obj) for obj in self.canonical])
		return "%s(%s)" % (type(self).__name__, canonicalStr)


class CanonicalCache(object):
	def __init__(self, create):
		self.create = create
		self.cache  = xcollections.weakcache()

	def __call__(self, *args):
		return self.cache[self.create(*args)]
