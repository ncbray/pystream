import util.compressedset

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

	def delAttr(self, attr):
		eq = self.getAttr(attr)
		assert eq is not None, "Attribute not found."
		del self.attrs[attr]
		eq.weight -= 1
		

	def absorb(self, other):
		self.hit    |= other.hit
		self.miss   |= other.miss
		self.weight += other.weight
		other.forward = self
		other.weight  = 0

		# Recursively absorb attributes...
		# NOTE other is forwarded, so the attributes of other won't change...
		for k, v in other:
			self.absorbAttr(k, v)

			# We might have gotten absorbed?
			self = self.getForward()

		return self

	def absorbAttr(self, attr, eq):
		existing = self.getAttr(attr)

		if existing is None:
			self.setAttr(attr, eq, steal=True)
		elif existing is not eq:
			if existing.weight >= eq:
				existing.absorb(eq)
			else:
				eq.absorb(existing)

	def copy(self, lut, kill, keepHits=False, keepMisses=False):
		if self in lut:
			return lut[self]
		else:
			cls = EquivalenceClass()
			lut[self] = cls

			cls.hit     = self.hit
			cls.miss    = self.miss
			cls.forward = None

			for attr, next in self:
				if attr in kill:
					if not (keepHits and next.hit or keepMisses and next.miss):
						continue
				other = next.copy(lut, kill, keepHits, keepMisses)
				cls.setAttr(attr, other)		
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
			
			print "%d (%d) %s" % (id(self), self.weight, hm)
			for k, v in self:
				print '\t', k, id(v)
			print

			for k, v in self:
				v.dump(processed)

	def inplaceIntersect(self, other, lut):
		key = (self, other)
		if key in lut:
			# HACK changed flag?
			return lut[key], False

		# Has the equivalence class been split into two?
		changed = self in lut

		eq = EquivalenceClass()
		# Cache it
		lut[key] = eq

		# Mark it as being visited
		lut[self] = True

		# Transfer hit
		if self.hit:
			if other.hit:
				eq.hit = True
			else:
				changed = True

		# Transfer miss
		if self.miss:
			if other.miss:
				eq.miss = True
			else:
				changed = True

		for k, v in self:
			ov = other.getAttr(k)
			if ov:
				newV, newChanged = v.inplaceIntersect(ov, lut)
				eq.setAttr(k, newV)
				changed |= newChanged
			else:
				changed = True

		return eq, changed

	def findExtended(self, canonical, path, newParam, processed):
		if self not in processed:
			processed.add(self)
			eparam = canonical.extendedParameterFromPath(path)
			newParam[eparam] = self
			for slot, eq in self:
				eq.findExtended(canonical, path+(slot,), newParam, processed)
			processed.remove(self)

	def extendParameters(self, canonical, parameters):
		for param in parameters:
			assert param.isSlot(), param
			
		processed = set()
		newParam  = {}

		# Find the extended parameters
		for slot, eq in self:
			if slot in parameters:
				eq.findExtended(canonical, (slot,), newParam, processed)

		# Root them
		# Done is a seperate stage to prevent wacking the previous iterator
		for eparam, eq in newParam.iteritems():
			self.setAttr(eparam, eq)

		# Report the new roots
		return set(newParam.iterkeys())

	def _splitHidden(self, extendedParameters, sharedEq, accessedCallback, lut, noKill):
		# NOTE will not prune pure non-accessed cycles
		# This is because the function assumes that all recursive cycles are non-pure.
		if self in lut:
			# Recurse
			return lut[self]
		else:
			# Shared nodes are considered pure, as they will be re-merged.
			initalPure = self in sharedEq
			
			eq = EquivalenceClass()
			eq.hit  = self.hit
			eq.miss = self.miss
			lut[self] = (eq, initalPure)

			# It's unsound to kill pure paths if there's more
			# than one way to get here, as one of the ways may be impure...
			noKill |= self.weight > 1

			# Copy unaccessable paths
			pure = True
			kill = []
			for slot, next in self:
				if accessedCallback(slot):
					# Node is impure
					pure = False
				else:
					newNext, newPure = next._splitHidden(extendedParameters, sharedEq, accessedCallback, lut, noKill)
					pure &= newPure
					eq.setAttr(slot, newNext)
					
					if newPure and slot not in extendedParameters:
						kill.append(slot)

			# Kill all of the pure paths.
			if not noKill:
				for slot in kill:
					self.delAttr(slot)

			# Are we pure, and didn't already know it?
			if pure and not initalPure:
				lut[self] = (eq, pure)
			
			return lut[self]

	def splitHidden(self, extendedParameters, accessedCallback):
		sharedEq = set()
		#sharedEq.add(self)
		for ep in extendedParameters:
			eq = self.getAttr(ep)
			if eq: sharedEq.add(eq)

		lut = {}

		hidden, pure = self._splitHidden(extendedParameters, sharedEq, accessedCallback, {}, False)		
		return hidden




class PathInformation(object):
	__slots__ = 'hits', 'root'

	def __init__(self, root=None):
		self.hits   = None

		if root is None:
			self.root  = EquivalenceClass()
		else:
			assert isinstance(root, EquivalenceClass), root
			self.root  = root
	

	def copy(self, kill=None, keepHits=False, keepMisses=False):
		if kill is None:
			kill = set()
		lut = {}
		root = self.root.copy(lut, kill, keepHits, keepMisses)
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
					largest = largest.absorb(eq.getForward())
				return largest
			else:
				return eqs.pop()

	def _markHit(self, path):
		cls = self.equivalenceClass(path, True)
		cls.hit = True

	def _markMiss(self, path):
		cls = self.equivalenceClass(path, True)
		cls.miss = True

	def unionHitMiss(self, additionalHits, additionalMisses):
		outp = self.copy()
		outp.inplaceUnionHitMiss(additionalHits, additionalMisses)
		return outp

	def inplaceUnionHitMiss(self, additionalHits, additionalMisses):
		# HACK should really be unioning hits?
		if additionalHits:
			#self.union(*additionalHits)
			for path in additionalHits:
				self._markHit(path)

		if additionalMisses:
			for path in additionalMisses:
				self._markMiss(path)
		return self


	def inplaceUnify(self, sys, e1, e0):
		self.union(e1, e0)

	def stableLocation(self, expr, slot, keepHits=False, keepMisses=False):
		path = expr.path()
		cls  = self.root

		# The :-1 due to the stable location.
		for attr in path[:-1]:
			if cls:
				next = cls.getAttr(attr)
				if attr is slot:
					if next and (keepHits and next.hit or keepMisses and next.miss):
						pass
					else:
						return False
				cls = next
			
			elif attr is slot:
				return False

		return True

	# Deletes set elements, therefore problematic.
	def filterUnstable(self, slot, keepHits=False, keepMisses=False):
		outp = self.copy(set([slot]), keepHits, keepMisses)
		return outp
		

	# Intersects equivilence sets, therefore problematic
	def inplaceMerge(self, other):
		lut = {}		
		newRoot, changed = self.root.inplaceIntersect(other.root, lut)

		if changed:
			self.root = newRoot

		return self, changed

	def extendParameters(self, canonical, parameterSlots):
		return self.root.extendParameters(canonical, parameterSlots)

	def dump(self):
		processed = set()
		self.root.dump(processed)

	def split(self, extendedParameters, accessedCallback):
		# NOTE mutates structure
		# NOTE is lossy, some equivalences that are not obviously accessable from
		# parameters but that may be mutated will be seperated from those that cannot
		# be mutated.
		# Example {s.n, t.m} will be lost if only n is accessed.
		return self, PathInformation(self.root.splitHidden(extendedParameters, accessedCallback))
