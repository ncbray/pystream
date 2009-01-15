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



### TODO filter out impossible hits?
##
##class PathInformation(object):
##	__slots__ = 'hits', 'misses', 'equivalence'
##
##	@classmethod
##	def fromHitMiss(cls, hits, misses, callback):
##		eq = UnionFind()
##		if hits: eq.union(*hits)
##		return cls(hits, misses, eq)
##
##	def __init__(self, hits, misses, equivalence):
##		assert isinstance(equivalence, UnionFind), equivalence
##		
##		# Validate
##		util.compressedset.validate(hits)
##		util.compressedset.validate(misses)
##
##		if hits:
##			self.hits = set([equivalence[path] for path in hits])
##		else:
##			self.hits = None
##
##
##		if misses:
##			self.misses = set()
##			for path in misses:
##				# Filter out trivial misses
##				if path in equivalence.parents or not path.slot.isLocal():
##					self.misses.add(equivalence[path])
##		else:
##			self.misses = None
##
##		self.equivalence = equivalence
##
##		self.checkInvariants()
##
##	def _rebuildHitMiss(self):		
##		if self.hits:
##			self.hits = set([self.equivalence[path] for path in self.hits])
##		else:
##			self.hits = None
##
##		if self.misses:
##			self.misses = set([self.equivalence[path] for path in self.misses])
##		else:
##			self.misses = None
##
##		if self.hits and self.misses:
##			assert not self.hits.intersection(self.misses)
##
##	def buildGrouping(self):
##		grouping = {}
##		for k in self.equivalence:
##			v = self.equivalence[k]
##			if v not in grouping:
##				grouping[v] = []
##			grouping[v].append(k)
##		return grouping
##
####	# HACK Really hackish and slow
####	def expandTree(self, sys, paths):
####		if paths:
####			output = set()
####			grouping = self.buildGrouping()
####			return self._expandTree(paths
####		
####		if paths:
####			output = set()
####			grouping = self.buildGrouping()
####
####			for path in paths:
####				group = self.equivalence[path]
####				if group in grouping:
####					output.update(grouping[group])
####				else:
####					output.add(path)
####		else:
####			return None
##	
##
##	def _expandTree(self, sys, paths, grouping):
##		if paths:
##			output = set()
##			grouping = self.buildGrouping()
##
##			for path in paths:
##				group = self.equivalence[path]
##				if group in grouping:
##					output.update(grouping[group])
##				else:
##					output.add(path)
##		else:
##			return None
##
##	def mustAlias(self, a, b):
##		return self.equivalence[a] == self.equivalence[b]
##
##	def enumerateMustAlias(self, paths):
##		# Assumes paths in canonical...
##		paths = self.canonicalSet(paths) # HACK?
##		if paths:
##			return paths.union([path for path in self.equivalence if self.equivalence[path] in paths])
##		else:
##			return None
##
##	def canonicalSet(self, paths):
##		if paths:
##			return set([self.equivalence[path] for path in paths])
##		else:
##			return None
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
##		e = self.equivalence[e]
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
##		newHits   = util.compressedset.union(self.hits, additionalHits)
##		newMisses = util.compressedset.union(self.misses, additionalMisses)
##
##		eq = self.equivalence.copy()
##		if additionalHits: eq.union(*newHits)
##		
##		return PathInformation(newHits, newMisses, eq)
##
##
##	def unify(self, sys, e1, e0):
##		e1Set = self.enumerateMustAlias(set((e1,)))
##		e0Set = self.enumerateMustAlias(set((e0,)))
##
##		#print "???", e0Set, e1Set
##		
##		def unifySet(paths):
##			for path in paths:
##				subs = path.substituteSet(sys, e1, e0Set)
##				if subs:
##					self.equivalence.union(path, *subs)
##
##		paths = self.equivalence.parents.keys()
##		unifySet(paths)
##		
##		# Nesisary to catch hits and misses that aren't in a group.
##		if self.hits:   unifySet(self.hits)
##		if self.misses: unifySet(self.misses)
##
##		self._rebuildHitMiss()
##
##	# Deletes set elements, therefore problematic.
##	def filterUnstable(self, sys, slot, stableValues):
##
##		stableValues = self.enumerateMustAlias(stableValues)
##		
##		newEquivalence = UnionFind()
##		rewrite = {}
##		for path in self.equivalence:
##			if path.stableValue(None, slot, stableValues):
##				group = self.equivalence[path]
##				if not group in rewrite:
##					rewrite[group] = path
##				else:
##					result = newEquivalence.union(rewrite[group], path)
##					#rewrite[group] = result
##		
##		def filterSet(s):
##			if s:
##				out = []
##				for path in s:
##					path = self.equivalence[path]
##					if path in rewrite:
##						out.append(rewrite[path])
##					elif path.stableValue(None, slot, stableValues):
##						out.append(path)
##				return out
##			else:
##				return None
##		
##		newHits   = filterSet(self.hits)
##		newMisses = filterSet(self.misses)
##		
##		return PathInformation(newHits, newMisses, newEquivalence)
##		
##
##	# Intersects equivilence sets, therefore problematic
##	def inplaceMerge(self, other):
##		newEquivalence = UnionFind()
##
##		pairs  = {}
##		hits   = set()
##		misses = set()
##		changed = False
##
##		for k in self.equivalence.parents.iterkeys():
##			if k in other.equivalence.parents.iterkeys():
##				selfg  = self.equivalence[k]
##				otherg = self.equivalence[k]
##				pairKey = (selfg, otherg)
##				if not pairKey in pairs:
##					pairs[pairKey] = k
##				else:
##					newEquivalence.union(pairs[pairKey], k)
##
##				selfHit,  selfMiss = self.classifyHitMiss(k)
##				otherHit, otherMiss = other.classifyHitMiss(k)
##
##				if selfHit:
##					if otherHit:
##						hits.add(k)
##					else:
##						changed = True		
##				if selfMiss:
##					if otherMiss:
##						if not k.slot.isLocal() or k in newEquivalence.parents:
##							misses.add(k)
##					else:
##						changed = True
##			else:
##				# HACK not sound
##				changed = True
##
##		self.equivalence = newEquivalence
##		self.hits   = self.canonicalSet(hits)
##		self.misses = self.canonicalSet(misses)
##
##		return self, changed
##
##	def extendParameters(self, sys, info):
##		# TODO turn this into a "unify" operation with mapping?
##		def extendSet(s):
##			if s:
##				for path in s:
##					eparam = path.makeExtendedParameter(sys, info.parameters)
##					if eparam:
##						self.equivalence.union(path, eparam)
##						info.extendedParameters.add(eparam)
##
##		extendSet(self.equivalence.parents.keys())
##		extendSet(self.hits)
##		extendSet(self.misses)
##
##		# HACK depends on how parameters are passed...
##		# this makes sure extended params are equivalent to all real parameters.
##		extendSet(info.parameters)
##
##		self._rebuildHitMiss()
##
##
##	def dump(self):
##		print "HITS"
##		paths = self.enumerateMustAlias(self.hits)
##		if paths:
##			for path in paths:
##				print path
##		print
##		print "MISSES"
##		paths = self.enumerateMustAlias(self.misses)
##		if paths:
##			for path in paths:
##				print path
##		print
##		print "EQUIVALENCES"
##		self.equivalence.dump()
##		print


class EquivalenceClass(object):
	__slots__ = 'attrs', 'hit', 'miss', 'forward', 'weight'

	def __init__(self):
		self.attrs   = None
		self.hit     = False
		self.miss    = False
		self.forward = None
		self.weight  = 0

	def __iter__(self):
		if self.attrs:
			for k in self.attrs.iterkeys():
				yield k, self.getAttr(k)

	def getForward(self):
		if self.forward:
			forward = self.forward.getForward()
			if self.forward is not forward:
				self.forward = forward
			return forward
		else:
			return self

	def getAttr(self, attr, create=False):
		if self.attrs and attr in self.attrs:
			eq = self.attrs[attr]

			while eq.forward is not None:
				eq = eq.getForward()
				self.attrs[attr] = eq

			assert eq is not None
			return eq
		elif create:
			return self.setAttr(attr, EquivalenceClass())
		else:
			return None

	def setAttr(self, attr, eq, steal=False):
		if self.attrs is None: self.attrs = {}
		assert not attr in self.attrs
		self.attrs[attr] = eq
		if not steal: eq.weight += 1
		return eq

	def absorb(self, other):
		self.hit    |= other.hit
		self.miss   |= other.miss
		self.weight += other.weight
		other.forward = self

		# Recursively absorb attributes...
		# NOTE other is forwarded, so the attributes of other won't change...
		for k, v in other:
			self.absorbAttr(k, v)

			# We might have gotten absorbed?
			self = self.getForward()

	def absorbAttr(self, attr, eq):
		existing = self.getAttr(attr)

		if existing is None:
			self.setAttr(attr, eq, steal=True)
		elif existing is not eq:
			if existing.weight >= eq:
				existing.absorb(eq)
			else:
				eq.absorb(existing)

	def copy(self, lut, kill):
		if self in lut:
			return lut[self]
		else:
			cls = EquivalenceClass()
			lut[self] = cls

			for attr, next in self:
				if attr not in kill:
					other = next.copy(lut, kill)
					cls.setAttr(attr, other)
			
			cls.hit     = self.hit
			cls.miss    = self.miss
			cls.forward = None
			cls.weight  = self.weight

			return cls

	def dump(self, processed):
		if not self in processed:
			processed.add(self)

			if self.hit:
				hm = 'hit'
			elif self.miss:
				hm = 'miss'
			else:
				hm = ''
			
			print id(self), hm
			for k, v in self:
				print '\t', k, id(v)
			print

			for k, v in self:
				v.dump(processed)

class PathInformation(object):
	__slots__ = 'hits', 'misses', 'root'

	@classmethod
	def fromHitMiss(cls, hits, misses, bogus):
		p = PathInformation()
		if hits: p.union(*hits)
		return p.unionHitMiss(hits, misses)


	def __init__(self, root=None):
		self.hits   = None
		self.misses = None

		if root is None:
			self.root  = EquivalenceClass()
		else:
			assert isinstance(root, EquivalenceClass), root
			self.root  = root
	

	def copy(self, kill=None):
		if kill is None:
			kill = set()
		lut = {}
		root = self.root.copy(lut, kill)
		return PathInformation(root)

	def equivalenceClass(self, expr, create=False):
		path = expr.path()

		cls = self.root
		
		for attr in path:
			cls = cls.getAttr(attr, create)
			if cls is None:
				assert not create
				return None

		return cls

	def getRoot(self, root, create=False):
		if root in self.root:
			cls = self.root[root]

	def partialEquivalence(self, expr):
		path = expr.path()

		cls = self.root

		for i, attr in enumerate(path):
			newCls = cls.getAttr(attr)
			if newCls:
				cls = newCls
			else:
				break
		return cls, path[i+1:]

	def mustAlias(self, a, b):
		if a is b: return True
		
		aCls, aPath = self.partialEquivalence(a)
		bCls, bPath = self.partialEquivalence(b)

		if aCls is bCls and aPath == bPath:
			return True
		else:
			return False

##	def enumerateMustAlias(self, paths):
##		# Assumes paths in canonical...
##		paths = self.canonicalSet(paths) # HACK?
##		if paths:
##			return paths.union([path for path in self.equivalence if self.equivalence[path] in paths])
##		else:
##			return None
##
##	def canonicalSet(self, paths):
##		if paths:
##			return set([self.equivalence[path] for path in paths])
##		else:
##			return None

	def classifyHitMiss(self, e):
		cls = self.equivalenceClass(e)
		if cls:
			return cls.hit, cls.miss
		else:
			return False, False

	def union(self, *paths):
		if len(paths) > 1:
			eqs = set([self.equivalenceClass(path, True) for path in paths])
			if len(eqs) > 1:
				largest = None
				for eq in eqs:
					if largest is None or eq.weight > largest.weight:
						largest = eq

				eqs.remove(largest)
				for eq in eqs:
					# Get forward is critical, as equivilence classes
					# may be recursively absorbed.
					largest.absorb(eq.getForward())

	def markHit(self, path):
		cls = self.equivalenceClass(path, True)
		cls.hit = True

	def markMiss(self, path):
		cls = self.equivalenceClass(path, True)
		cls.miss = True

	def unionHitMiss(self, additionalHits, additionalMisses):
		outp = self.copy()

		# HACK should really be unioning misses?
		if additionalHits:
			for path in additionalHits:
				outp.markHit(path)

		if additionalMisses:
			for path in additionalMisses:
				outp.markMiss(path)
		return outp


	def unify(self, sys, e1, e0):
		self.union(e1, e0)

	# Deletes set elements, therefore problematic.
	def filterUnstable(self, sys, slot, stableValues):
		outp = self.copy(set([slot]))
		return outp
		

##	# Intersects equivilence sets, therefore problematic
##	def inplaceMerge(self, other):
##		newEquivalence = UnionFind()
##
##		pairs  = {}
##		hits   = set()
##		misses = set()
##		changed = False
##
##		for k in self.equivalence.parents.iterkeys():
##			if k in other.equivalence.parents.iterkeys():
##				selfg  = self.equivalence[k]
##				otherg = self.equivalence[k]
##				pairKey = (selfg, otherg)
##				if not pairKey in pairs:
##					pairs[pairKey] = k
##				else:
##					newEquivalence.union(pairs[pairKey], k)
##
##				selfHit,  selfMiss = self.classifyHitMiss(k)
##				otherHit, otherMiss = other.classifyHitMiss(k)
##
##				if selfHit:
##					if otherHit:
##						hits.add(k)
##					else:
##						changed = True		
##				if selfMiss:
##					if otherMiss:
##						if not k.slot.isLocal() or k in newEquivalence.parents:
##							misses.add(k)
##					else:
##						changed = True
##			else:
##				# HACK not sound
##				changed = True
##
##		self.equivalence = newEquivalence
##		self.hits   = self.canonicalSet(hits)
##		self.misses = self.canonicalSet(misses)
##
##		return self, changed

	def extendParameters(self, sys, info):
		for param in info.parameters:
			eparam = param.makeExtendedParameter(sys, info.parameters)
			info.extendedParameters.add(eparam)
			self.union(param, eparam)

		# TODO reach for dotted paths?


	def dump(self):
		processed = set()
		self.root.dump(processed)
