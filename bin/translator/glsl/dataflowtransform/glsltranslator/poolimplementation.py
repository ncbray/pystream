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
