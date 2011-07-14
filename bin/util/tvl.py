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

__all__ = ('TVLType', 'TVLTrue', 'TVLFalse', 'TVLMaybe', 'tvl')

# Three-valued logic: True/Maybe/False

# Abstract base class
class TVLType(object):
	__slots__ = ()

	def __nonzero__(self):
		#return self.maybeTrue()
		raise TypeError, ("%r cannot be directly converted a boolean value." % self)

	def certain(self):   return True
	def uncertain(self): return False

class TVLTrueType(TVLType):
	def maybeTrue(self):   return True
	def maybeFalse(self):  return False
	def mustBeTrue(self):  return True
	def mustBeFalse(self): return False
	def __repr__(self):    return 'TVLTrue'
	def __invert__(self):  return TVLFalse

	def __and__(self, other):
		return other

	def __rand__(self, other):
		return other

	def __or__(self, other):
		return self

	def __ror__(self, other):
		return self

	def __xor__(self, other):
		return ~other

	def __rxor__(self, other):
		return ~other

class TVLFalseType(TVLType):
	__slots__ = ()

	def maybeTrue(self):   return False
	def maybeFalse(self):  return True
	def mustBeTrue(self):  return False
	def mustBeFalse(self): return True
	def __repr__(self):    return 'TVLFalse'
	def __invert__(self):  return TVLTrue

	def __and__(self, other):
		return self

	def __rand__(self, other):
		return self

	def __or__(self, other):
		return other

	def __ror__(self, other):
		return other

	def __xor__(self, other):
		return other

	def __rxor__(self, other):
		return other

class TVLMaybeType(TVLType):
	__slots__ = ()

	def maybeTrue(self):   return True
	def maybeFalse(self):  return True
	def mustBeTrue(self):  return False
	def mustBeFalse(self): return False

	def certain(self):     return False
	def uncertain(self):   return True

	def __repr__(self):    return 'TVLMaybe'
	def __invert__(self):  return self

	def __and__(self, other):
		if isinstance(other, TVLFalseType):
			return other
		else:
			return self

	def __rand__(self, other):
		if isinstance(other, TVLFalseType):
			return other
		else:
			return self

	def __or__(self, other):
		if isinstance(other, TVLTrueType):
			return other
		else:
			return self

	def __ror__(self, other):
		if isinstance(other, TVLTrueType):
			return other
		else:
			return self

	def __xor__(self, other):
		return self

	def __rxor__(self, other):
		return self

TVLTrue     = TVLTrueType()
TVLFalse    = TVLFalseType()
TVLMaybe    = TVLMaybeType()

def tvl(obj):
	if isinstance(obj, TVLType):
		return obj
	else:
		return TVLTrue if obj else TVLFalse
