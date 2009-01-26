import sys

class SlotManager(object):
	def __init__(self):
		self.slots = {}

	def _getExistingValue(self, sys, slot):
		s = slot.createInital(sys)
		self.slots[slot] = s
		return s

	def read(self, sys, slot):
		if slot is None:
			# vargs, etc. can be none
			# Returning an iterable None allows it to be
			# used in a product transparently.
			return (None,)
		else:
#			assert isinstance(slot, AbstractSlot), slot
			result = self.slots.get(slot)
			if result is None:
				result = self._getExistingValue(sys, slot)
			return result

	def update(self, sys, slot, values):
#		assert isinstance(slot, AbstractSlot), repr(slot)
#		for value in values:
#			assert isinstance(value, extendedtypes.ExtendedType), repr(value)

		target = self.slots.get(slot)
		if target is None:
			# If the slot is unitialized, pull the inital value from the heap.
			target = self._initialize(sys, slot)

		diff = set(values)-target
		if diff:
			self.slots[slot].update(diff)
			sys.slotChanged(slot)

	def iterslots(self):
		return self.slots.iteritems()

	def slotMemory(self):
		mem = sys.getsizeof(self.slots)
		for slot, values in self.slots.iteritems():
			mem += sys.getsizeof(values)
		return mem


class CachedSlotManager(SlotManager):
	def __init__(self):
		SlotManager.__init__(self)
		self.cache = {}

	def _getExistingValue(self, sys, slot):
		s = frozenset(slot.createInital(sys))
		s = self.cache.setdefault(s, s)
		self.slots[slot] = s
		return s

	def update(self, sys, slot, values):
#		assert isinstance(values, (set, frozenset)), type(values)
#		assert isinstance(slot, AbstractSlot), repr(slot)
#		for value in values:
#			assert isinstance(value, extendedtypes.ExtendedType), repr(value)

		target = self.slots.get(slot)
		if target is None:
			# If the slot is unitialized, pull the inital value from the heap.
			target = self._getExistingValue(sys, slot)

		diff = values-target
		if diff:
			s = target.union(diff)
			self.slots[slot] = self.cache.setdefault(s, s)
			sys.slotChanged(slot)

	def slotMemory(self):
		mem = sys.getsizeof(self.slots)
		mem += sys.getsizeof(self.cache)

		for s1, s2 in self.cache.iteritems():
			mem += sys.getsizeof(s1)

		return mem
