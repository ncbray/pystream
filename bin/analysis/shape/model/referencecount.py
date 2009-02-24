from util.tvl import *

class ReferenceCountManager(object):
	def __init__(self):
		self.absoluteLUT = {}
		self.incrementLUT = {}
		self.decrementLUT = {}

		self.k = 2
		self.infinity = self.k+1

		self.null = self.getCanonical({}, ())

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
		if rc:
			assert isinstance(rc, ReferenceCount), type(rc)
			counts = rc.counts
			radius = rc.radius
		else:
			counts = {}
			radius = frozenset()

		if slot.isHeap():
			newrc = dict(counts)
			newRadius = radius
			newrc[slot] = min(newrc.get(slot, 0)+1, self.infinity)
		elif slot.isLocal():
			newrc = counts
			assert slot not in radius, radius
			newRadius = radius.union((slot,))
		else:
			assert False, slot

		canonical = self.getCanonical(newrc, newRadius)

		assert canonical is not None
		assert canonical.slotHit(slot).mustBeTrue(), slot

		return (canonical,)


	def makeDecrement(self, rc, slot):
		assert isinstance(rc, ReferenceCount), type(rc)
		assert rc.slotHit(slot).mustBeTrue(), slot
		counts = rc.counts
		radius = rc.radius

		if slot.isHeap():
			newrc = dict(counts)
			newRadius = radius
			exists = False
			saturated = False


			count = newrc[slot]
			if count == self.infinity:
				newrc[slot] = self.k
				saturated = True
			elif count > 1:
				newrc[slot] = count-1
			else:
			      del newrc[slot]

			canonical = self.getCanonical(newrc, newRadius)

			if saturated:
				return (canonical, rc)
			else:
				# Even if canonical is empty.
				return (canonical,)
		elif slot.isLocal():
			assert slot in radius, radius
			canonical = self.getCanonical(counts, radius-frozenset((slot,)))
			return (canonical,)
		else:
			assert False, slot

	def getCanonical(self, rc, radius):
		# Validate the reference counts
		for slot, count in rc.iteritems():
			assert slot.isHeap(), slot
			assert count > 0 and count <= self.infinity, count

		for slot in radius:
			assert slot.isLocal(), slot

		radius = frozenset(radius)
		key = (frozenset(rc.iteritems()), radius)

		if key not in self.absoluteLUT:
			obj = ReferenceCount(rc, radius)
			self.absoluteLUT[key] = obj
		else:
			obj = self.absoluteLUT[key]
		return obj


	def split(self, rc, valid):
		validrc   = {}
		invalidrc = {}

		for slot, count in rc.counts.iteritems():
			if slot in valid:
				validrc[slot] = count
			else:
				invalidrc[slot] = count

		validradius = []
		invalidradius = []

		for slot in rc.radius:
			if slot in valid:
				validradius.append(slot)
			else:
				invalidradius.append(slot)

		a = self.getCanonical(validrc, validradius)
		b = self.getCanonical(invalidrc, invalidradius)

		#assert self.merge(a, b) is rc
		return a, b

	def merge(self, a, b):
		# Assumes the reference counts are disjoint.
		newrc = {}
		if a: newrc.update(a.counts)
		if b: newrc.update(b.counts)
		return self.getCanonical(newrc, a.radius.union(b.radius))

class ReferenceCount(object):
	__slots__ = 'counts', 'radius'

	def __init__(self, counts, radius):
		assert isinstance(counts, dict), type(counts)
		self.counts = counts
		self.radius = radius

	def __repr__(self):
		rc = ["%s=%s" % p for p in self.counts.iteritems()]
		rc.extend([str(r) for r in self.radius])
		return "rc(%s)" % ", ".join(rc)

	def slotHit(self, slot):
		if slot.isHeap():
			return tvl(slot in self.counts)
		elif slot.isLocal():
			return tvl(slot in self.radius)
		else:
			assert False, slot

	def isExpression(self):
		return False

	def __len__(self):
		return len(self.counts)+len(self.radius)

	def forget(self, sys, kill):
		newcounts = {}
		for slot, count in self.counts.iteritems():
			if slot not in kill:
				newcounts[slot] = count

		newradius = frozenset([slot for slot in self.radius if slot not in kill])

		return sys.canonical.rcm.getCanonical(newcounts, newradius)

	def remap(self, sys, slotMapping):
		newcounts = {}
		for slot, count in self.counts.iteritems():
			newslot = slotMapping.get(slot, slot)
			if newslot:
				newcounts[newslot] = count

		newradius = []
		for slot in self.radius:
			newslot = slotMapping.get(slot, slot)
			if newslot:
				newradius.append(newslot)

		newradius = frozenset(newradius)

		return sys.canonical.rcm.getCanonical(newcounts, newradius)

