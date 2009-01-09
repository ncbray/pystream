from analysis.database import lattice

class SecondaryInformation(object):
	__slots__ = 'hits', 'misses', 'externalReferences'
	def __init__(self, hits, misses, externalReferences):
		lattice.setIntersectionSchema.validate(hits)
		lattice.setIntersectionSchema.validate(misses)

		self.hits   = hits if hits else None
		self.misses = misses if misses else None
		self.externalReferences = externalReferences

	def merge(self, other):
		hits, hitsChanged = lattice.setIntersectionSchema.inplaceMerge(self.hits, other.hits)
		if hitsChanged: self.hits = hits

		misses, missesChanged = lattice.setIntersectionSchema.inplaceMerge(self.misses, other.misses)
		if missesChanged: self.misses = misses


		if self.externalReferences == False and other.externalReferences == True:
			self.externalReferences = True
			externalChanged = True
		else:
			externalChanged = False

		return hitsChanged or missesChanged or externalChanged

	def __repr__(self):
		return "secondary(hits=%r, misses=%r, external=%r)" % (self.hits, self.misses, self.externalReferences)

	def copy(self):
		hits   = lattice.setIntersectionSchema.copy(self.hits)
		misses = lattice.setIntersectionSchema.copy(self.misses)
		return SecondaryInformation(hits, misses, self.externalReferences)


emptyInformation = SecondaryInformation(None, None, False)
