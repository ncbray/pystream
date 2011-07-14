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

class Slot(object):
	__slots__ = 'region'

	def isSlot(self):
		return True

	def isExpression(self):
		return False

	def isConfiguration(self):
		return False

	def isLocal(self):
		return False

	def isHeap(self):
		return False

	def isField(self):
		return False

	def isParameter(self):
		return False

	def isExtendedParameter(self):
		return False

	def isAgedParameter(self):
		return False

	def age(self, canonical):
		return self

	def unage(self):
		return self


class LocalSlot(Slot):
	__slots__ = 'lcl'
	def __init__(self, lcl):
		self.lcl = lcl

	def isLocal(self):
		return True

	def isParameter(self):
		return isinstance(self.lcl, (int, str))

	def __repr__(self):
		return "lcl(%s)" % str(self.lcl)

class FieldSlot(Slot):
	__slots__ = 'heap', 'field'

	def __init__(self, heap, field):
		self.heap   = heap
		self.field  = field

	def isHeap(self):
		return True

	def isField(self):
		return True

	def __repr__(self):
		return repr(self.field)
		#return "field(%s, %s)" % (str(self.heap), str(self.field))
