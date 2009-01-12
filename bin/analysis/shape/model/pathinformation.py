import util.compressedset

class PathInformation(object):
	__slots__ = 'hits', 'misses'

	def __init__(self, hits, misses):
		# Validate
		util.compressedset.validate(hits)
		util.compressedset.validate(misses)

		if hits:
			for hit in hits:
				assert hit.isExpression(), hit

		if misses:
			for miss in misses:
				assert miss.isExpression(), miss

		self.hits   = hits if hits else None
		self.misses = misses if misses else None

	def classifyHitMiss(self, e):
		isHit  = e in self.hits if self.hits else False
		isMiss = e in self.misses if self.misses else False
		return isHit, isMiss
	
	def inplaceMerge(self, other):
		hits, hitsChanged = util.compressedset.inplaceIntersection(self.hits, other.hits)
		if hitsChanged: self.hits = hits

		misses, missesChanged = util.compressedset.inplaceIntersection(self.misses, other.misses)
		if missesChanged: self.misses = misses

		return self, (hitsChanged or missesChanged)

	def copy(self):
		hits   = util.compressedset.copy(self.hits)
		misses = util.compressedset.copy(self.misses)
		return PathInformation(hits, misses)

	def unionHitMiss(self, additionalHits, additionalMisses):
		# HACK?
		newHits   = util.compressedset.union(self.hits,   additionalHits)
		newMisses = util.compressedset.union(self.misses, additionalMisses)
		return PathInformation(newHits, newMisses)
