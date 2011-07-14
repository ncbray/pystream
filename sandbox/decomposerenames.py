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

import sys

from renamelut import data, different

import collections

from PADS.StrongConnectivity import StronglyConnectedComponents
from PADS.UnionFind import UnionFind

import fuzzyorder

def setgraph(domain):
	g = {}
	for d in domain:
		g[d] = set()
	return g

def listgraph(domain):
	g = {}
	for d in domain:
		g[d] = []
	return g

def filteredSCC(G):
	o = []
	for g in StronglyConnectedComponents(G):
		if len(g) > 1:
			o.append(g)
	return o

def partitionGraph(G):
	u = UnionFind()
	for node, next in G.iteritems():
		u.union(node, *next)

	mapping = {}
	for node in G.iterkeys():
		mapping[node] = u[node]

	domain = set(mapping.itervalues())

	groups = setgraph(domain)

	for node, group in mapping.iteritems():
		groups[group].add(node)

	for d in domain:
		assert d in groups

	return domain, groups, mapping


def partitionRenames(data, domain, mapping):
	new = {}
	external = {}

	for d in domain:
		new[d] = {}
		external[d] = set()

	links = {}
	for rank, renames in data.iteritems():
		for rename in renames:
			# Partition portions of the rename
			partition = collections.defaultdict(list)
			link = []
			for k, v in rename.iteritems():
				if mapping[k] == mapping[v]:
					partition[mapping[k]].append(k)
				else:
					link.append(k)

			# Build a rename for each group
			for g, p in partition.iteritems():
				newrename = {}
				for k in p:
					newrename[k] = rename[k]

				for k, v in newrename.iteritems():
					assert mapping[k] == mapping[v]

				if not rank in new[g]:
					new[g][rank] = []

				new[g][rank].append(newrename)

			# Build renames that link partitions
			newrename = {}
			for k in link:
				newrename[k] = rename[k]
				external[mapping[k]].add(k)
				external[mapping[v]].add(v)
			if not rank in links:
				links[rank] = []

			links[rank].append(newrename)

	return new, links, external

def graphFromRenames(data, domain, keepOne=False):
	G = setgraph(domain)
	for rank, renames in data.iteritems():
		for rename in renames:
			if len(rename) > 1 or keepOne:
				for k, v in rename.iteritems():
					G[k].add(v)
	return G


# Calculate the domain
domain = set()
for rank, renames in data.iteritems():
	for rename in renames:
		for k, v in rename.iteritems():
			domain.add(k)
			domain.add(v)

for defs in different:
	domain.update(defs)


# Merging partitions should be conflict free.
# Find and kill conflicts in the root partiton.
# Merging

def process(data, domain, external, level=0):

	#if not 600 in domain: return

	G = graphFromRenames(data, domain)
	groupdomain, groups, mapping = partitionGraph(G)
	groupedrenames, links, externalrefs = partitionRenames(data, groupdomain, mapping)

	numlinks = 0
	for rank, renames in links.iteritems():
		numlinks += len(renames)


	print '\t'*level, len(domain), '/', len(external), groupdomain, numlinks


	if len(groupdomain) > 1:
		order = []
		mapping = {}
		for d in groupdomain:
			gext = external.intersection(groups[d]).union(externalrefs[d])
			no, nm = process(groupedrenames[d], groups[d], gext, level+1)

			order.extend(no)
			mapping.update(nm)

		orderLUT = {}
		for i, d in enumerate(order):
			orderLUT[d] = i

		orderLUT = fuzzyorder.composeMappings(mapping, orderLUT)

		mapping = tryCollapse(data, domain, external, orderLUT)
		return order, mapping
	else:
		return handleLeaf(data, domain, external, G, level+1)

class ConsistancyGroups(object):
	def __init__(self):
		self.group = UnionFind()


	def addConstraint(self, x, y):
		fx, fy = (x[1],x[0]), (y[1],y[0])
		assert not self.group[x] == self.group[fy]
		assert not self.group[fx] == self.group[y]
		self.group.union(x, y)
		self.group.union(fx, fy)

	def getGroups(self):
		glut = {}
		lut = {}

		for p in self.group:
			g = self.group[p]
			if not g in glut:
				glut[g] = set()

			glut[g].add(p)
			lut[p] = glut[g]

		return lut

def extractSubranges(a, b, orderLUT, level):
	if len(a) > 1:
		for i in range(1, len(b)):
			if orderLUT[b[0]] >= orderLUT[b[i]]:
				print '\t'*level, "(%d, %d) ^ (%d, %d)" % (a[0], a[i], b[0], b[i])
			else:
				l.append({a[0]:b[0], a[i]:b[i]})

		extractSubranges(a[1:], b[1:], orderLUT, level, l)

def extractInconsistancies(rank, rename, orderLUT, level):
	a = sorted(rename.iterkeys(), key=lambda e:orderLUT[e])
	b = [rename[x] for x in a]


	#print a, b
	oa, ob = [orderLUT[x] for x in a], [orderLUT[x] for x in b]
	if fuzzyorder.isSwap(ob) or fuzzyorder.isDegenerate(ob):
		print '\t'*level, "inconsistant", rank, rename

		extractSubranges(a, b, orderLUT, level)
	else:
		return [rename]

def registerPair(precedes, follows, x):
	precedes[x[1]].add(x[0])
	follows[x[0]].add(x[1])


def extractOrderSubranges(precedes, follows, a, b, orderLUT):
	if len(a) > 1:
		for i in range(1, len(b)):
			registerPair(precedes, follows, (a[0], a[i]))

			if orderLUT[b[0]] >= orderLUT[b[i]]:
				print "(%d, %d) ^ (%d, %d)" % (a[0], a[i], b[0], b[i])

				if b[i] != b[0]:
					registerPair(precedes, follows, (b[i], b[0]))
			else:
				registerPair(precedes, follows, (b[0], b[i]))

		extractOrderSubranges(precedes, follows, a[1:], b[1:], orderLUT)

def extractOrder(precedes, follows, rename, orderLUT):
	a = sorted(rename.iterkeys(), key=lambda e:orderLUT[e])
	b = [rename[x] for x in a]

	oa, ob = [orderLUT[x] for x in a], [orderLUT[x] for x in b]
##	if fuzzyorder.isSwap(ob) or fuzzyorder.isDegenerate(ob):
##		print '\t'*level, "inconsistant", rank, rename

	extractOrderSubranges(precedes, follows, a, b, orderLUT)


def mustBeDifferent(different, l):
	for a in l:
		for b in l:
			if a!=b:
				different[a].add(b)
				different[b].add(a)

def extractPartialOrder(data, domain, external, orderLUT):
	precedes  = setgraph(domain)
	follows   = setgraph(domain)
	different = setgraph(domain)


	mustBeDifferent(different, external)

	for rank, renames in data.iteritems():
		for rename in renames:
			mustBeDifferent(different, rename.keys())
			mustBeDifferent(different, rename.values())

			extractOrder(precedes, follows, rename, orderLUT)

	precedes = fuzzyorder.makeClosure(precedes, domain)
	follows = fuzzyorder.makeClosure(follows, domain)

	for p, s in precedes.iteritems():
		assert not p in s, p

	for p, s in follows.iteritems():
		assert not p in s, p


	return precedes, follows, different

def tryCollapse(data, domain, external, orderLUT):
	precedes, follows, different = extractPartialOrder(data, domain, external, orderLUT)

	fuser = fuzzyorder.Fuser(precedes, follows, different)

	ranks = sorted(data.iterkeys(), reverse=True)

	def tryFuse(rename, giveup=True):
		for k, v in rename.iteritems():
			if fuser.canFuse(k, v):
				fuser.doFuse(k, v)
			elif giveup:
				break
	skipped = []
	for rank in ranks:
		renames = data[rank]
		for rename in renames:
			# TODO skip problematic?
			for k, v in rename.iteritems():
				# Can we completely fuse?
				if not fuser.canFuse(k, v):
					skipped.append(rename)
			else:
				tryFuse(rename)


	mapping = {}
	for d in domain:
		mapping[d] = fuser.union[d]

	newdomain = set(mapping.values())
	print "LEN", len(newdomain)

	return mapping


def makeAnalogySubranges(a, b, orderLUT, out):
	if len(a) > 1:
		for i in range(1, len(b)):

			if orderLUT[b[0]] >= orderLUT[b[i]]:
				print "(%d, %d) ^ (%d, %d)" % (a[0], a[i], b[0], b[i])

				if b[0] != b[i]:
					out.append(((a[0], a[i]), (b[i], b[0])))
			else:
				out.append(((a[0], a[i]), (b[0], b[i])))

		makeAnalogySubranges(a[1:], b[1:], orderLUT, out)

def makeAnalogies(data, orderLUT):
	out = []
	for rank, renames in data.iteritems():
		for rename in renames:


			a = sorted(rename.iterkeys(), key=lambda e:orderLUT[e])
			b = [rename[x] for x in a]

			makeAnalogySubranges(a, b, orderLUT, out)
	return out

def handleLeaf(data, domain, external, G, level):

##	print
##	print
##
##	print domain
##	print external
##	print data

	ranks = sorted(data.iterkeys(), reverse=True)

##	for rank in ranks:
##		print rank
##		for rename in data[rank]:
##			print '\t', rename


	if data:
##		for scc in filteredSCC(graphFromRenames(data, domain, True)):
##			print '\t'*level, len(scc), scc


		order, orderLUT = fuzzyorder.findBestOrder(data, domain, 0.99)

		mapping = tryCollapse(data, domain, external, orderLUT)

##		mapping = fuser.makeMapping(domain)
##		newdata = fuzzyorder.translateData(data, mapping)
##		fuzzyorder.printViolations(newdata)


		if 97 in domain:
			fo = open('leaf_dump.py', 'w')
			fo.write('data = ')
			fo.write(repr(data))
			fo.write('\n')
			fo.write('domain = ')
			fo.write(repr(domain))
			fo.write('\n')

			fo.write('external = ')
			fo.write(repr(external))
			fo.write('\n')

			fo.write('analogies = ')
			fo.write(repr(makeAnalogies(data, orderLUT)))
			fo.write('\n')

			fo.close()


		return list(order), mapping
	else:
		mapping = {}
		for d in domain:
			mapping[d] = d

		return list(domain), mapping

order, mapping = process(data, domain, set())



lut = {}
for i, d in enumerate(order):
	lut[d] = i

#lut = fuzzyorder.composeMappings(mapping, lut)



ordereddata = fuzzyorder.translateData(data, lut)

fuzzyorder.printViolations(ordereddata)
print "Domains: ", fuzzyorder.mappingResultSize(lut)


sys.exit()





G = setgraph(domain)
B = setgraph(domain)
u = UnionFind()

for rank, renames in data.iteritems():
	for rename in renames:
		for k, v in rename.iteritems():
			G[k].add(v)
			B[v].add(k)
			u.union(k, v)


# Find the disjoint subgraphs
groupmap = {}
for d in domain:
	groupmap[d] = u[d]
groupnames = set(groupmap.itervalues())

groups  = setgraph(groupnames)
for d in domain:
	groups[groupmap[d]].add(d)

# Build the interference graph

interference = setgraph(domain)
for defn in different:
	for a in defn:
		for b in defn:
			if  a != b:
				interference[a].add(b)




# Find loops in the rename graph
loops = filteredSCC(G)


print "Groups", len(groupnames)
for name, group in groups.iteritems():
	print name, len(group)
print


print "Loops", len(loops)
for loop in loops:
	example = loop.keys()[0]

	loopset = set(loop.keys())

	print groupmap[example], loop

	pure = True
	for e in loopset:
		inter = interference[e].intersection(loopset)
		if inter:
			print '\t', e, inter
			pure = False
print


# Find the order analogies for each group.
class Analogy(object):
	def __init__(self, a, b, rank):
		self.a = a
		self.b = b
		self.rank = rank


analogies = listgraph(groupnames)
for rank, renames in data.iteritems():
	for rename in renames:
		partition = collections.defaultdict(list)

		# Group the rename terms
		for k in rename.iterkeys():
			partition[groupmap[k]].append(k)

		# Build analogies for each group
		for g, p in partition.iteritems():
			if len(p) > 1:
				a = Analogy(p, [rename[x] for x in p], rank)
				analogies[g].append(a)


print "Analogies"
for g, al in analogies.iteritems():
	print g, '\t', len(al)


print "Analogy groups"
for g, al in analogies.iteritems():
	u = UnionFind()
	live = set()
	for a in al:
		u.union(*a.a)
		u.union(*a.b)
		live.update(a.a)
		live.update(a.b)

	seperate = set()
	for l in live:
		seperate.add(u[l])

	sgroups = setgraph(seperate)
	for l in live:
		sgroups[u[l]].add(l)

	print g, '\t', len(seperate)


	sgroupnext = setgraph(seperate)
	for a in al:
		ag = u[a.a[0]]
		bg = u[a.b[0]]
		sgroupnext[ag].add(bg)

	sloops = filteredSCC(sgroupnext)

	print "\tResolutions loops"
	for e in sloops:
		print '\t', e
	print



##	for n, s in sgroups.iteritems():
##		print '\t', n, len(s)
