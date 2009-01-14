import util.compressedset
from .. import path

if False:
	from PADS.UnionFind import UnionFind
	class UnionFind(UnionFind):
		def copy(self):
			u = UnionFind()
			u.parents.update(self.parents)
			u.weights.update(self.weights)
			return u

		def dump(self):
			for k, v in self.parents.iteritems():
				print "%r  ->  %r" % (k, v)
else:
	UnionFind = path.UnionFind

##class PathInformation(object):
##	__slots__ = 'hits', 'misses', 'equivalence'
##
##	@classmethod
##	def fromHitMiss(cls, hits, misses, callback):
##		eq = path.PathEquivalence(callback)
##		if hits:
##			eq.union(*hits)
##			hits = eq.canonicalSet(hits)
##
##		if misses:
##			misses = eq.canonicalSet(misses)
##
##		return cls(hits, misses, eq)
##
##	def __init__(self, hits, misses, equivalence):
##		# Validate
##		util.compressedset.validate(hits)
##		util.compressedset.validate(misses)
##
##		if hits:
##			for hit in hits:
##				assert hit.isExpression(), hit
##
##		if misses:
##			for miss in misses:
##				assert miss.isExpression(), miss
##
##
##		self.hits   = hits if hits else None
##		self.misses = misses if misses else None
##		self.equivalence = equivalence
##
##		self.checkInvariants()
##
##	def checkInvariants(self):
##		assert not self.hits or len(self.hits) == 1, self.hits
##
##		if self.hits and self.misses:
##			intersection = self.hits.intersection(self.misses)
##			assert not intersection, intersection
##
##
##	def classifyHitMiss(self, e):
##		e = self.equivalence.canonical(e)
##		isHit  = e in self.hits if self.hits else False
##		isMiss = e in self.misses if self.misses else False
##		return isHit, isMiss
##	
##
##	def copy(self):
##		hits   = util.compressedset.copy(self.hits)
##		misses = util.compressedset.copy(self.misses)
##		equiv  = self.equivalence.copy()
##		return PathInformation(hits, misses, equiv)
##
##	def unionHitMiss(self, additionalHits, additionalMisses):
##		eq = self.equivalence.copy()
##		eq.union(*additionalHits)
##
##		newHits   = eq.canonicalSet(util.compressedset.union(self.hits,   additionalHits))
##		newMisses = eq.canonicalSet(util.compressedset.union(self.misses, additionalMisses))
##		
##		return PathInformation(newHits, newMisses, eq)
##
##
##	def unify(self, sys, e1, e0):
##		self.equivalence.union(e1, e0)
##		self.hits   = self.equivalence.canonicalSet(self.hits)
##		self.misses = self.equivalence.canonicalSet(self.misses)
##
##	# Deletes set elements, therefore problematic.
##	def filterUnstable(self, sys, slot, stableValues):
##		#stableValues = self.equivalence.canonicalSet(stableValues)
##		
##		def filterUnstable(sys, exprs, slot, stableValues):
##			if exprs:
##				if exprs is stableValues:
##					# Optimization, all the values are known stable, so just check the locations.
##					return util.compressedset.copy([e for e in exprs if e.stableLocation(sys, slot, stableValues)])
##				else:	
##					return util.compressedset.copy([e for e in exprs if e.stableValue(sys, slot, stableValues)])
##			else:
##				return util.compressedset.nullSet
##
##		equivalence = self.equivalence.filterUnstable(slot, stableValues)
##		
##		newHits   = filterUnstable(sys, self.hits,   slot, stableValues)
##		newMisses = filterUnstable(sys, self.misses, slot, stableValues)
##		return PathInformation.fromHitMiss(newHits, newMisses, self.equivalence._callback)
##
##	# Intersects equivilence sets, therefore problematic
##	def inplaceMerge(self, other):
##		hits, hitsChanged = util.compressedset.inplaceIntersection(self.hits, other.hits)
##		if hitsChanged: self.hits = hits
##
##		misses, missesChanged = util.compressedset.inplaceIntersection(self.misses, other.misses)
##		if missesChanged: self.misses = misses
##
##		# TODO intersect equivilence set
##
##		return self, (hitsChanged or missesChanged)



# TODO filter out impossible hits?

class PathInformation(object):
	__slots__ = 'hits', 'misses', 'equivalence'

	@classmethod
	def fromHitMiss(cls, hits, misses, callback):
		eq = UnionFind()
		if hits: eq.union(*hits)
		return cls(hits, misses, eq)

	def __init__(self, hits, misses, equivalence):
		assert isinstance(equivalence, UnionFind), equivalence
		
		# Validate
		util.compressedset.validate(hits)
		util.compressedset.validate(misses)

		if hits:
			self.hits = set([equivalence[path] for path in hits])
		else:
			self.hits = None


		if misses:
			self.misses = set()
			for path in misses:
				# Filter out trivial misses
				if path in equivalence.parents or not path.slot.isLocal():
					self.misses.add(equivalence[path])
		else:
			self.misses = None

		self.equivalence = equivalence

		self.checkInvariants()

	def _rebuildHitMiss(self):		
		if self.hits:
			self.hits = set([self.equivalence[path] for path in self.hits])
		else:
			self.hits = None

		if self.misses:
			self.misses = set([self.equivalence[path] for path in self.misses])
		else:
			self.misses = None

		if self.hits and self.misses:
			assert not self.hits.intersection(self.misses)


	def enumerateMustAlias(self, paths):
		if paths:
			return paths.union([path for path in self.equivalence if self.equivalence[path] in paths])
		else:
			return None

	def canonicalSet(self, paths):
		return set([self.equivalence[path] for path in paths])

	def checkInvariants(self):
		assert not self.hits or len(self.hits) == 1, self.hits

		if self.hits and self.misses:
			intersection = self.hits.intersection(self.misses)
			assert not intersection, intersection


	def classifyHitMiss(self, e):
		e = self.equivalence[e]
		isHit  = e in self.hits if self.hits else False
		isMiss = e in self.misses if self.misses else False
		return isHit, isMiss
	

	def copy(self):
		hits   = util.compressedset.copy(self.hits)
		misses = util.compressedset.copy(self.misses)
		equiv  = self.equivalence.copy()
		return PathInformation(hits, misses, equiv)

	def unionHitMiss(self, additionalHits, additionalMisses):
		newHits   = util.compressedset.union(self.hits, additionalHits)
		newMisses = util.compressedset.union(self.misses, additionalMisses)

		eq = self.equivalence.copy()
		if additionalHits: eq.union(*newHits)
		
		return PathInformation(newHits, newMisses, eq)


	def unify(self, sys, e1, e0):
		def unifySet(paths):
			for path in paths:
				subs = path.substitute(sys, e1, e0)
				if subs:
					self.equivalence.union(path, subs)

		paths = self.equivalence.parents.keys()
		unifySet(paths)
		
		# Nesisary to catch hits and misses that aren't in a group.
		if self.hits:   unifySet(self.hits)
		if self.misses: unifySet(self.misses)

		self._rebuildHitMiss()

	# Deletes set elements, therefore problematic.
	def filterUnstable(self, sys, slot, stableValues):

		stableValues = self.enumerateMustAlias(stableValues)
		
		newEquivalence = UnionFind()
		rewrite = {}
		for path in self.equivalence:
			if path.stableValue(None, slot, stableValues):
				group = self.equivalence[path]
				if not group in rewrite:
					rewrite[group] = path
				else:
					result = newEquivalence.union(rewrite[group], path)
					#rewrite[group] = result
		
		def filterSet(s):
			if s:
				out = []
				for path in s:
					path = self.equivalence[path]
					if path in rewrite:
						out.append(rewrite[path])
					elif path.stableValue(None, slot, stableValues):
						out.append(path)
				return out
			else:
				return None
		
		newHits   = filterSet(self.hits)
		newMisses = filterSet(self.misses)
		
		return PathInformation(newHits, newMisses, newEquivalence)
		

	# Intersects equivilence sets, therefore problematic
	def inplaceMerge(self, other):
		newEquivalence = UnionFind()

		pairs  = {}
		hits   = set()
		misses = set()
		changed = False

		for k in self.equivalence.parents.iterkeys():
			if k in other.equivalence.parents.iterkeys():
				selfg  = self.equivalence[k]
				otherg = self.equivalence[k]
				pairKey = (selfg, otherg)
				if not pairKey in pairs:
					pairs[pairKey] = k
				else:
					newEquivalence.union(pairs[pairKey], k)

				selfHit,  selfMiss = self.classifyHitMiss(k)
				otherHit, otherMiss = other.classifyHitMiss(k)

				if selfHit:
					if otherHit:
						hits.add(k)
					else:
						changed = True		
				if selfMiss:
					if otherMiss:
						if not k.slot.isLocal() or k in newEquivalence.parents:
							misses.add(k)
					else:
						changed = True
			else:
				# HACK not sound
				changed = True

		self.equivalence = newEquivalence
		self.hits   = self.canonicalSet(hits)
		self.misses = self.canonicalSet(misses)

		return self, changed
