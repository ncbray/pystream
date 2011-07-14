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

from language.glsl import ast as glsl
from . slotstruct import SlotStruct

import re
invalidNameChar = re.compile('[^\w\d_]')

# HACK does not ensure the first character is not a digit.
def ensureValidName(name):
	return re.sub(invalidNameChar, '_', name)

# A pool contains O objects and F fields.
class PoolImplementation(object):
	def __init__(self, poolinfo, basename):
		self.poolinfo = poolinfo

		# HACK
		poolinfo.impl = self

		self.basename = basename
		self.stores   = {}
		self.types    = {}

		self.struct = SlotStruct(poolinfo)

		#self.struct.dump()
		#print

	def _getFieldRef(self, field, slotinfo):
		key = field, slotinfo
		if not key in self.stores:
			fieldimpl = slotinfo.getPoolInfo().impl
			t = fieldimpl.struct.ast

			name = "%s_%s_%s" % (self.basename, field.type, field.name.pyobj)
			name = ensureValidName(name)
			lcl  = glsl.Local(t, name)
			self.stores[key] = lcl
		else:
			lcl = self.stores[key]

		return lcl

	def _deref(self, ref, index):
		if self.poolinfo.isSingleUnique():
			return ref
		else:
			return glsl.GetSubscript(ref, index)

	def getType(self, index):
		assert self.poolinfo.typeTaken
		#assert False, "hack"

		return glsl.Load(index, 'type')

	def getField(self, index, field, slotinfo):
		assert slotinfo.isSlotInfo(), slotinfo
		ref = self._getFieldRef(field, slotinfo)
		return self._deref(ref, index)

	def getValue(self, index, type):
		assert self.struct.inlined
		return index

	def allocate(self, translator, slot, g):
		if self.poolinfo.isSingleUnique():
			return []
		else:
			src = translator.slotRef(translator.makeConstant(0), slot)
			return translator.assignmentTransfer(src, g)
