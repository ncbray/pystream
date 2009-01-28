import sys

from . import storegraph
from programIR.python import program

class SlotManager(object):
	def __init__(self, sys):
		self.sys   = sys
		self.slots = {}

#	def _getExistingValue(self, slot):
#		s = slot.createInital(self.sys)
#		self.slots[slot] = s
#		return s

#	def initialize(self, slot, *values):
#		return self.update(slot, frozenset(values))


#	def read(self, slot):
#		if slot is None:
#			# vargs, etc. can be none
#			# Returning an iterable None allows it to be
#			# used in a product transparently.
#			return (None,)
#		else:
##			assert isinstance(slot, AbstractSlot), slot
#			result = self.slots.get(slot)
#			if result is None:
#				result = self._getExistingValue(slot)
#			return result

#	def update(self, slot, values):
#		target = self.slots.get(slot)

#		# If the slot is unitialized, pull the inital value from the heap.
#		if target is None: target = self._getExistingValue(slot)

#		diff = values-target
#		if diff:
#			self.slots[slot].update(diff)
#			self.sys.slotChanged(slot)

#	def iterslots(self):
#		return self.slots.iteritems()

	def slotMemory(self):
		mem = sys.getsizeof(self.slots)
		for slot, values in self.slots.iteritems():
			mem += sys.getsizeof(values)
		return mem


class CachedSlotManager(SlotManager):
	def __init__(self, sys):
		self.sys = sys
		self.cache = {}

		emptyset = frozenset()
		self._emptyset = self.cache.setdefault(emptyset, emptyset)

		# HACK to store local variables...
		self.roots  = storegraph.RegionGroup()
		self.region = storegraph.RegionNode(None)

	# TODO we're passing sys, so eventually this method can be removed...
	def root(self, sys, name, regionHint):
		return self.roots.root(sys, name, regionHint)

	def knownRoot(self, name):
		return self.roots.knownRoot(name)

	def emptyTypeSet(self):
		return self._emptyset

	def inplaceUnionTypeSet(self, a, b):
		c = a.union(b)
		return self.cache.setdefault(c, c)

	def diffTypeSet(self, a, b):
		return a-b

	def slotMemory(self):
		mem = sys.getsizeof(self.cache)
		for s1, s2 in self.cache.iteritems():
			mem += sys.getsizeof(s1)
		return mem


	def existingSlotRef(self, xtype, slotName):
		assert xtype.isExisting()
		assert not slotName.isRoot()

		obj = xtype.obj
		assert isinstance(obj, program.AbstractObject), obj
		self.sys.ensureLoaded(obj)

		slottype, key = slotName.type, slotName.name

		assert isinstance(key, program.AbstractObject), key

		if isinstance(obj, program.Object):
			if slottype == 'LowLevel':
				subdict = obj.lowlevel
			elif slottype == 'Attribute':
				subdict = obj.slot
			elif slottype == 'Array':
				subdict = obj.array
			elif slottype == 'Dictionary':
				subdict = obj.dictionary
			else:
				assert False, slottype

			if key in subdict:
				return self.sys.canonical.existingType(subdict[key])

		# Not found
		return None
