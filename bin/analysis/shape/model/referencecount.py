class ReferenceCountManager(object):
	def __init__(self):
		self.absoluteLUT = {}
		self.incrementLUT = {}
		self.decrementLUT = {}

		self.k = 2
		self.infinity = self.k+1

	def increment(self, rc, slot):
		key = (rc, slot)
		lut = self.incrementLUT
		
		if not key in lut:
			newrc = self.makeIncrement(rc, slot)
			lut[key] = newrc
		else:
			newrc = lut[key]

		return newrc

	def decrement(self, rc, slot):
		key = (rc, slot)
		lut = self.decrementLUT
		
		if not key in lut:
			newrc = self.makeDecrement(rc, slot)
			lut[key] = newrc
		else:
			newrc = lut[key]
		return newrc


	def makeIncrement(self, rc, slot):
		newrc = []
		exists = False

		if rc:
			assert isinstance(rc, ReferenceCount), type(rc)
			
			for existingslot, count in rc.counts:
				if existingslot == slot:
					newcount = min(count+1, self.infinity)
					newrc.append((existingslot, newcount))
					exists = True
				else:
					newrc.append((existingslot, count))

		if not exists:
			newrc.append((slot, 1))

		canonical = self.getCanonical(newrc)

		assert canonical is not None

		return (canonical,)


	def makeDecrement(self, rc, slot):
		newrc = []
		exists = False
		saturated = False

		assert isinstance(rc, ReferenceCount), type(rc)

		for existingslot, count in rc.counts:
			if existingslot == slot:
				if count == self.infinity:
					newrc.append((existingslot, self.k))
					saturated = True
				elif count > 1:
					newrc.append((existingslot, count-1))


				exists = True
			else:
				newrc.append((existingslot, count))

		assert exists

		
		canonical = self.getCanonical(newrc)

		if saturated:
			return (canonical, rc)
		else:
			# Even if canonical is empty.
			return (canonical,)		

	def getCanonical(self, rc):
##		if not len(rc):
##			return None

		# Validate the reference counts
		fields = set()
		for slot, count in rc:
			if slot in fields:
				assert False, "Two counts for the same field: %r" % slot
			else:
				fields.add(slot)

		rc = frozenset(rc)
		
		if not rc in self.absoluteLUT:
			obj = ReferenceCount(rc)
			self.absoluteLUT[rc] = obj
		else:
			obj = self.absoluteLUT[rc]

		return obj


	def split(self, rc, valid):
		validrc   = []
		invalidrc = []
		
		for slot, count in rc.counts:
			if slot in valid:
				validrc.append((slot, count))
			else:
				invalidrc.append((slot, count))

		return self.getCanonical(validrc), self.getCanonical(invalidrc)

	def merge(self, a, b):
		# Assumes the reference counts are disjoint.
		newrc = []
		if a: newrc.extend(a.counts)
		if b: newrc.extend(b.counts)
		return self.getCanonical(newrc)

class ReferenceCount(object):
	__slots__ = 'counts'

	def __init__(self, counts):
		self.counts = counts

	def __repr__(self):
		return "rc(%s)" % ", ".join(["%s=%s" % rc for rc in self.counts])

	def referedToBySlot(self, slot):
		#assert slot.isSlot(), slot
		# Ugly and slow.
		for rslot, count in self.counts:
			if rslot == slot:
				return True
		return False

	def isExpression(self):
		return False

	def __len__(self):
		return len(self.counts)
