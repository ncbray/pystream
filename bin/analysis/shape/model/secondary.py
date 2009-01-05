from analysis.database import lattice

class SecondaryInformation(object):
	__slots__ = 'hits', 'misses'
	def __init__(self, hits, misses):
		lattice.setIntersectionSchema.validate(hits)
		lattice.setIntersectionSchema.validate(misses)

		self.hits   = hits if hits else None
		self.misses = misses if misses else None

	def merge(self, other):
		hits, hitsChanged = lattice.setIntersectionSchema.inplaceMerge(self.hits, other.hits)
		if hitsChanged: self.hits = hits

		misses, missesChanged = lattice.setIntersectionSchema.inplaceMerge(self.misses, other.misses)
		if missesChanged: self.misses = misses

		return hitsChanged or missesChanged

	def __repr__(self):
		return "secondary(hits=%r, misses=%r)" % (self.hits, self.misses)

	def copy(self):
		hits   = lattice.setIntersectionSchema.copy(self.hits)
		misses = lattice.setIntersectionSchema.copy(self.misses)
		return SecondaryInformation(hits, misses)


emptyInformation = SecondaryInformation(None, None)
