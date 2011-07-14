# Copyright 2011 Nicholas Bray
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import collections

import time

class AbsoluteOrderConstraint(object):
	__slots__ = 'a', 'b', 'weight'

	def __init__(self, a, b, weight):
		self.a = a
		self.b = b
		self.weight = weight

	def best(self):
		return self.weight

	def specialize(self, x, c):
		if x == self.a:
			c.addScore(self.weight)
		elif x == self.b:
			pass
		else:
			self.attach(c)

	def attach(self, c):
		c.addConstraint(self, self.weight)
		c.hot.add(self.a)
		c.hot.add(self.b)
		c.gain[self.a] += self.weight
		c.loss[self.b] += self.weight

	def __str__(self):
		return "%s < %s -> %f" % (self.a, self.b, self.weight)


class RelativeOrderConstraint(object):
	__slots__ = 'a', 'b', 'c', 'd', 'weight', 'cache'
	def __init__(self, a, b, c, d, weight):
		self.a = a
		self.b = b
		self.c = c
		self.d = d
		self.weight = weight

		self.cache = (AbsoluteOrderConstraint(c,d,weight),
			      AbsoluteOrderConstraint(d,c,weight),
			      AbsoluteOrderConstraint(a,b,weight),
			      AbsoluteOrderConstraint(b,a,weight))

	def specialize(self, x, c):
		situation = 0

		if x == self.a:
			situation += 1
		elif x == self.b:
			situation += 2

		if x == self.c:
			situation += 4
		elif x == self.d:
			situation += 8


		if situation == 0:
			self.attach(c)
		elif situation == 1:
			self.cache[0].attach(c)
		elif situation == 2:
			self.cache[1].attach(c)
		elif situation == 4:
			self.cache[2].attach(c)
		elif situation == 8:
			self.cache[3].attach(c)
		elif situation == 5:
			c.addScore(self.weight)
		elif situation == 10:
			c.addScore(self.weight)
		elif situation == 6:
			pass
		elif situation == 9:
			pass
		else:
			assert False


	def attach(self, c):
		c.addConstraint(self, self.weight)
		c.active.add(self.a)
		c.active.add(self.b)
		c.active.add(self.c)
		c.active.add(self.d)

	def __str__(self):
		return "(%s, %s) ~ (%s, %s) -> %f" % (self.a, self.b, self.c, self.d, self.weight)

class Constraints(object):
	def __init__(self, order, score):
		self.order	 = order
		self.score       = score

		self.constraints = []
		self.possible    = 0.0

		self.active  = set()
		self.hot     = set()
		self.gain    = collections.defaultdict(lambda: 0.0)
		self.loss    = collections.defaultdict(lambda: 0.0)

	def addScore(self, amt):
		self.score += amt

	def addConstraint(self, c, amt):
		self.constraints.append(c)
		self.possible += amt

	def specialize(self, x):
		child = Constraints(self.order+(x,), self.score)
		for c in self.constraints:
			c.specialize(x, child)

		assert child.score >= self.score
		assert child.possible <= self.possible
		assert len(child.constraints) <= len(self.constraints)
		return child

	def dump(self):
		print self.order
		print self.score, "/", self.possible
		for c in self.constraints:
			print c
		print

	def optimisticScore(self):
		return self.score+self.possible

	def pessimisticScore(self):
		return self.score

	def __le__(self, other):
		#return self.optimisticScore() >= other.optimisticScore()
		return self.pessimisticScore() >= other.pessimisticScore()

class IsomorphismCache(object):
	def __init__(self):
		self.cache = {}
		self.hits = 0
		self.kills = 0

	def check(self, c):
		state = tuple(c.constraints)
		existing = self.cache.get(state)

		if existing is None:
			self.cache[state] = c
			return True
		else:
			self.hits += 1
			if c.score > existing.score:
				return True
				self.cache[state] = c
			else:
				self.kills += 1
				return False


class Searcher(object):
	def __init__(self, similar, tolerance):
		self.checked = 0
		self.lowerbound = 0.0
		self.best = None
		self.iso = IsomorphismCache()

		self.optimistic = 0.0

		self.similar = similar
		self.tolerance = tolerance

	def process(self, c):
		start = time.clock()
		c = self.contractTrivial(c)
		self.optimistic = c.optimisticScore()
		self.handleNode(c)

		end = time.clock()

		#print "Elapsed", end-start

		return self.best

	def handleNode(self, c):
		optimistic = c.optimisticScore()
		if not self.worthChecking(optimistic):
			return

		self.checked += 1


		if self.checked%1000 == 0:
			print self.lowerbound, len(c.order), c.optimisticScore(), c.pessimisticScore()
			print self.lowerbound/self.optimistic
			print (optimistic-self.lowerbound)/self.optimistic
			#print self.iso.kills, self.iso.hits, len(self.iso.cache)
			print

		if self.checked%10000 == 0 and self.best:
			self.best.dump()


		if not c.constraints:
			if optimistic >= self.lowerbound:
				self.best = c
				self.lowerbound = optimistic

				if self.lowerbound >= self.optimistic*self.tolerance:
					# If we're close enough to the best possible,
					# go for it.
					self.lowerbound = self.optimistic*1.1
		else:
			self.lowerbound = max(self.lowerbound, c.pessimisticScore())
			self.generateChildren(c)

	def worthChecking(self, optimistic):
		return (optimistic-self.lowerbound)/self.optimistic > 0.0001

	def generateChildren(self, c):
		optimistic = c.optimisticScore()

		for symbol in self.order(c):
			if not self.worthChecking(optimistic):
				break

			child = c.specialize(symbol)
			child = self.contractTrivial(child)
			if self.iso.check(child):
				self.handleChild(child)

	def contractTrivial(self, c):
		trivial = []

		for symbol in c.hot:
			if not symbol in c.active:
				if c.gain[symbol] and not c.loss[symbol]:
					trivial.append(symbol)

		if trivial:
			for symbol in trivial:
				c = c.specialize(symbol)
			return self.contractTrivial(c)
		else:
			return c

	def handleChild(self, c):
		self.handleNode(c)

	def order(self, c):
		if False:
			if c.order:
				similar = self.similar[c.order[-1]]
			else:
				similar = set()

			hottest = similar.intersection(c.hot).union(similar.intersection(c.active))

			h = list(hottest)
			h.sort(key=lambda e: c.loss[e]-c.gain[e])
			h.extend(c.hot)
			h.extend(c.active)

		else:
			h = list(c.hot)
			h.sort(key=lambda e: c.loss[e]-c.gain[e])
			h.extend(c.active)

		return h




def fuseOrderedRenames(data, diffs, numNames):
	lbounds = collections.defaultdict(lambda: -1)
	rbounds = collections.defaultdict(lambda: numNames)


	weights = collections.defaultdict(dict)
	totalweight = 0.0

	def handleDif(d):
		# Inequality constraints
		for x in d:
			for y in d:
				if x<y and x > lbounds[y]: lbounds[y] = x
				if x>y and x < rbounds[y]: rbounds[y] = x

	for d in diffs:
		handleDif(d)

	for rank, renames in data.iteritems():
		for rename in renames:
			# Original
			a = sorted(rename.iterkeys())
			b = [rename[x] for x in a]

			#handleDif(a)
			#handleDif(b)

			for ax, bx in zip(a, b):
				if ax == bx: continue
				if ax > bx: ax, bx = bx, ax

				weight = float(rank)
				if not bx in weights[ax]:
					weights[ax][bx] = weight
				else:
					weights[ax][bx] += weight

				totalweight += weight

	# Partition using dynamic programming.
	#partitions[i] -> (start, total)
	partitions = []
	for i in range(numNames):
	#for i in range(21):
		if i == 0:
			partitions.append((0, 0.0))
		else:
			best = (i, partitions[i-1][1])
			runningscore = 0.0

			lbound = lbounds[i]

			for p in reversed(range(0, i)):
				if p <= lbound:
					break

				# Calculate the effect of adding p to the partition.
				for dest, value in weights[p].iteritems():
					if dest <= i:
						runningscore += value
				lbound = max(lbound, lbounds[p])

				# Get the previous partition score.
				if p == 0:
					score = 0.0
				else:
					score = partitions[p-1][1]

				total = score+runningscore
				if total >= best[1]:
					best = (p, total)

			partitions.append(best)



	# Collect the partitions.
	out = []
	prev = numNames-1
	while prev >= 0:
		start, score = partitions[prev]
		out.append((start, prev))
		prev = start-1
	out.reverse()


##	for i in range(numNames):
##		print lbounds[i], i, rbounds[i]


	groupLUT = {}

	def fuse(a, b):
		groupLUT[b] = groupLUT.get(a, a)

	unique = 0

	for a, b in out:
		unique += 1
		for x in range(a, b+1):
			groupLUT[x] = a
##			if not x in groupLUT:
##				unique += 1
##				groupLUT[x] = x
##
##			for target, weight in weights[x].iteritems():
##				if target <= b:
##					groupLUT[target] = groupLUT[x]


	totalscore = partitions[-1][1]
	print "Collapse score", totalscore/totalweight
	print "Unique names", unique, unique/float(numNames)

	return groupLUT

def collapseNames(data):
	live = set()
	for rank, renames in data.iteritems():
		for rename in renames:
			for k, v in rename.iteritems():
				live.add(k)
				live.add(v)

	live = sorted(live)

	lut = {}
	current = 0

	for old in live:
		lut[old] = current
		current += 1

	return lut

def createInfo(data, defs):
	follows   = collections.defaultdict(set)
	precedes  = collections.defaultdict(set)
	similar   = collections.defaultdict(set)
	different = collections.defaultdict(set)

	remaining = set()

	def addPartialOrder(l):
		while len(l) > 1:
			a, b = l[0], l[1]
			if a != b:
				# Degenerate?
				follows[a].add(b)
				precedes[b].add(a)

				# Excessive?
				different[a].add(b)
				different[b].add(a)
			l = l[1:]

	for defn in defs:
		for a in defn:
			for b in defn:
				if a != b:
					different[a].add(b)
					different[b].add(a)
		remaining.update(defn)

	for rank, renames in data.iteritems():
		for rename in renames:
			addPartialOrder(sorted(rename.iterkeys()))
			#b = [rename[x] for x in a]
			addPartialOrder(sorted(rename.itervalues()))


			for k, v in rename.iteritems():
				# Why is this nessisary?
				remaining.add(k)
				remaining.add(v)

				assert k in remaining, k
				assert v in remaining, v
				similar[k].add(v)
				similar[v].add(k)

	current = set()
	for x in remaining:
		if not precedes[x]:
			current.add(x)

	return follows, precedes, similar, different, remaining, current

def collapseRenames2(data, defs):
	follows, precedes, similar, different, remaining, current = createInfo(data, defs)

	group = 0
	groupset = set()
	groupsimilar   = collections.defaultdict(lambda: 0.0)
	groupdifferent = set()

	mapping = {}

	#assert 85 in different[86], different[86]

	while current:
		choice = None
		best = 0.0
		for k, v in groupsimilar.iteritems():
			if k in current and v > best:
				assert not k in groupdifferent
				choice = k
				best = v

		if choice is None:
			possible = current-groupdifferent
			if possible:
				choice = possible.pop()

		if choice is not None:
			assert not choice in groupdifferent

			remaining.remove(choice)
			current.remove(choice)

			groupset.add(choice)
			mapping[choice] = group

			if choice in groupsimilar:
				del groupsimilar[choice]

			# Find any new nodes.
			for next in follows[choice]:
				precedes[next].remove(choice)
				if not precedes[next]:
					current.add(next)

			groupdifferent.update(different[choice])
			for d in different[choice]:
				if d in groupsimilar:
					del groupsimilar[d]
				#different[d].remove(choice)

			for s in similar[choice]:
				if not s in groupdifferent:
					groupsimilar[s] += 1.0
				#similar[s].remove(choice)
		else:
			group += 1
			groupset.clear()
			groupsimilar.clear()
			groupdifferent.clear()

	if remaining:
		for r in remaining:
			print r
			print precedes[r]
			print follows[r]
			print similar[r]
			print different[r]
			print

	print mapping
	print group

	return mapping


def makeClosure(lut, domain):
	closure   = {}
	for r in domain:
		closure[r] = set()

	for p, s in lut.iteritems():
		closure[p].update(s)

	changed = True
	while changed:
		changed = False
		for p, s in closure.iteritems():
			new = set()
			for n in s: new.update(closure[n])
			dif = new-s
			if dif:
				s.update(dif)
				changed = True

	# Check consistancy
	for p, s in closure.iteritems():
		for n in s:
			assert closure[n].issubset(s)

	return closure

import PADS.UnionFind


class Fuser(object):
	def __init__(self, precedes, follows, different):
		self.union 	= PADS.UnionFind.UnionFind()
		self.precedes 	= precedes
		self.follows	= follows
		self.different 	= different

	def canonical(self, a, b):
		return self.union[a], self.union[b]

	def canFuse(self, a, b):
		a, b = self.canonical(a, b)

		if a == b:
			return True

		# HACK
		#self.update(a)
		#self.update(b)


		if not self.checkHalf(a, b): return False
		if not self.checkHalf(b, a): return False

		return True

	def checkHalf(self, a, b):
		if a in self.different[b]:
			return False

		if a in self.precedes[b] or a in self.follows[b]:
			return False

		if self.follows[a].intersection(self.precedes[b]):
			return False

		assert not a in self.follows[a]
		assert not a in self.precedes[a]
		assert not a in self.different[a]

		return True

	def translateSet(self, s):
		return set([self.union[e] for e in s])


	def update(self, d):
		self.follows[d]   = self.translateSet(self.follows[d])
		self.precedes[d]  = self.translateSet(self.precedes[d])
		self.different[d] = self.translateSet(self.different[d])

	def doFuse(self, a, b):
		a, b = self.canonical(a, b)
		assert self.canFuse(a, b)

		if a!=b:
			self.union.union(a, b)
			new = self.union[a]

			self.update(a)
			self.update(b)

			self.follows[new]   = self.follows[a].union(self.follows[b])
			self.precedes[new]  = self.precedes[a].union(self.precedes[b])
			self.different[new] = self.different[a].union(self.different[b])

			# Ugly and expensive?
			for p in self.precedes[new]:
				#self.update(p)
				self.follows[p].update(self.follows[new])

			for p in self.follows[new]:
				#self.update(p)
				self.precedes[p].update(self.precedes[new])


			assert not new in self.follows[new]
			assert not new in self.precedes[new]
			assert not new in self.different[new]


	def makeOrder(self, domain):
		#print "Ordering"

		newdomain = set()
		for d in domain:
			newdomain.add(self.union[d])

		for d in newdomain:
			self.update(d)

		current = set()
		ranked = set()
		remaining = set(newdomain)
		rank = 0


		# Problematically, this may fuse domains of different types?
		opprotunistic = False

		order = {}
		currentID = 0
		while remaining:
			current.clear()
			exemplars = set()
			for d in remaining:
				if self.precedes[d].issubset(ranked):

					for e in exemplars:
						if self.canFuse(e, d):
							self.doFuse(e, d)
							order[d] = order[e]
							break
					else:
						order[d] = currentID
						currentID += 1

						if opprotunistic:
							exemplars.add(d)

					current.add(d)


			assert current

			#print "Rank %d: %s" % (rank, current)
			ranked.update(current)
			remaining.difference_update(current)
			rank += 1

		print "Ranks: %d" % rank

		return order

	def makeMapping(self, domain):
		order = self.makeOrder(domain)

		mapping ={}
		for d in domain:
			mapping[d] = order[self.union[d]]
			#mapping[d] = self.union[d]

		return mapping

##	gen = 0
##
##	next = set()
##	while current:
##		assert isinstance(next, set)
##		assert isinstance(current, set)
##
##
##		for c in current:
##			remaining.remove(c)
##			mapping[c] = gen
##
##			for follow in follows[c]:
##				precedes[follow].remove(c)
##				if not precedes[follow]:
##					next.add(follow)
##
##		current,next = next,current
##		next.clear()
##		gen += 1
##
##	print "Generations:", gen
##
##	assert not remaining

def collapseRenames(data, defs, boundry=1000000000):
	follows, precedes, similar, different, remaining, current = createInfo(data, defs)

	mapping = {}

	precedesC = makeClosure(precedes, remaining)
	followsC = makeClosure(follows, remaining)

	boundryset = frozenset(range(boundry, len(remaining)))


	# Doesn't seem to help?
	for x, s in precedesC.iteritems():
		if x >= boundry:
			s.difference_update(boundryset)

	for x, s in followsC.iteritems():
		if x >= boundry:
			s.difference_update(boundryset)


	fuser = Fuser(precedesC, followsC, different)

	ranks = sorted(data.iterkeys(), reverse=True)

	def tryFuse(rename, giveup=True):
		for k, v in rename.iteritems():
			if fuser.canFuse(k, v):
				fuser.doFuse(k, v)
			elif giveup:
				break

	skipped = []
	broken  = []

	print "Fuse easy"
	for rank in ranks:
		renames = data[rank]
		for rename in renames:
			a, b = flattenRename(rename)
			if isSwap(b) or isDegenerate(b):
				broken.append(rename)
			else:
				for k, v in rename.iteritems():
					# Can we completely fuse?
					if not fuser.canFuse(k, v):
						skipped.append(rename)
						break
				else:
					tryFuse(rename)

	print "Fuse difficult"
	for skip in skipped:
		tryFuse(skip, False)

	print "Fuse problematic"
	for broke in broken:
		tryFuse(broke, False)

	mapping = fuser.makeMapping(remaining)

	print
	print "Unique after fusion: ", mappingResultSize(mapping), len(remaining)
	print

	return mapping

def translateData(data, lut):
	out = {}
	for rank, renames in data.iteritems():
		out[rank] = []
		for rename in renames:
			new = {}
			doesrename = False
			for k, v in rename.iteritems():
				tk = lut[k]
				tv = lut[v]

				assert tk not in new, ("Degenerate key?", rename)

				new[tk] = tv

				if tk != tv:
					doesrename = True
			if doesrename:
				out[rank].append(new)
	return out


def translateDefs(defs, lut):
	new = []
	for defn in defs:
		new.append(frozenset([lut[t] for t in defn]))
	return new

def translate(data, defs, lut):
	return translateData(data, lut), translateDefs(defs, lut)

def sanityCheck(data, defs, count):
	for rank, renames in data.iteritems():
		for rename in renames:
			for k, v in rename.iteritems():
				assert k < count, rename
				assert v < count, rename

	for defn in defs:
		for t in defn:
			assert t<count,defn

def simplifyRename(rename):
	simp = {}
	for k, v in rename.iteritems():
		if k != v:
			simp[k] = v
	return simp


def flattenRename(rename):
	a = sorted(rename.iterkeys())
	b = [rename[x] for x in a]
	return a, b

def isSwap(b):
	# HACK
	return b != sorted(b)

def isDegenerate(b):
	for i in b:
		if b.count(i) != 1:
			return True
	return False

def printViolations(data):
	print
	print "=== Rename Violations ==="
	print

	pure = 0
	total = 0

	for rank, renames in data.iteritems():
		for rename in renames:
			#rename = simplifyRename(rename)
			a, b = flattenRename(rename)

			if isSwap(b):
				print rank, "Swap ", a, b
			elif isDegenerate(b):
				print rank, "Degen", a, b

			total += 1



	print "Total: ", total
	print

###############

def similarSets(data):
	similar = collections.defaultdict(set)

	for rank, renames in data.iteritems():
		for rename in renames:
			for k, v in rename.iteritems():
				similar[k].add(v)
				similar[v].add(k)

	return similar

def addPairs(c, a, b, weight):
	assert len(a) == len(b)

	if len(a) > 1:
		ah, bh = a[0], b[0]
		at, bt = a[1:], b[1:]

		for ax, bx in zip(at, bt):
			if ah == ax or bh == bx:
				continue
			if ah==bx and bh==ax:
				continue
			if ah==bh and ax==bx:
				continue

			RelativeOrderConstraint(ah, ax, bh, bx, weight).attach(c)

			# Crossterm alignment
			RelativeOrderConstraint(ah, bx, bh, ax, weight*0.2).attach(c)

		addPairs(c, at, bt, weight)

def mappingResultSize(mapping):
	return len(set(mapping.itervalues()))

def composeMappings(a, b):
	comp = {}

	for k, v in a.iteritems():
		comp[k] = b[v]

	return comp

def findBestOrder(data, domain, tol=0.95):
	# Build the constraints.
	c = Constraints((), 0.0)
	for rank, renames in data.iteritems():
		for rename in renames:
			a = rename.keys()
			a.sort()
			b = [rename[x] for x in a]

			n = len(a)
			if n > 1:
				#weight = 1.0/(n*(n-1))*rank
				weight = 1.0/n*rank
				#weight = 1.0*(rank+1.0)*0.1
				addPairs(c, a, b, weight)



	similar = similarSets(data)
	search = Searcher(similar, tol)
	best = search.process(c)

##	print
##	print "Score ratio: %f" % (best.pessimisticScore()/c.optimisticScore())
##	print "Checked: %d" % search.checked

	bound = set(best.order)
	unbound = domain-bound

	order = list(best.order)
	boundry = len(order)
	order.extend(unbound)


	orderLUT = {}
	for i, d in enumerate(order):
		orderLUT[d] = i

	#print "Boundry: %d/%d" % (boundry, len(order))


	return order, orderLUT

def remap(data, defs, tol=0.95):
	domain = set()
	for rank, renames in data.iteritems():
		for rename in renames:
			for i in rename.iteritems():
				domain.update(i)
	for defn in defs:
		domain.update(defn)



	order, orderLUT = findBestOrder(data, domain, tol)

	data, defs = translate(data, defs, orderLUT)
	sanityCheck(data, defs, len(order))


##	print
##	print "Ordered"
##	printViolations(data)

	n = mappingResultSize(orderLUT)

	result = orderLUT

	if True:
		lut = collapseRenames(data, defs, boundry)
		data, defs = translate(data, defs, lut)
		result = composeMappings(result, lut)

		n = mappingResultSize(lut)
		sanityCheck(data, defs, n)

		print
		print "Collapsed"
		printViolations(data)


	if False:
		groupLUT = fuseOrderedRenames(data, defs, n)
		data, defs = translate(data, defs, groupLUT)
		result = composeMappings(result, groupLUT)


		clut = collapseNames(data)
		data, defs = translate(data, defs, clut)
		result = composeMappings(result, clut)

##		print
##		print "Fused"
##		printViolations(data)

	#assert 65 in live
	#assert 65 in result

	return result

if __name__ == '__main__':
	import psyco
	psyco.full()

	from renamelut import data, different, proposed

	result = remap(data, different)
	print result
