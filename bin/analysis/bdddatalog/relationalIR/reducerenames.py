from __future__ import absolute_import

from util.visitor import StandardVisitor

import PADS.UnionFind

from .. datalogIR import datalogast

import fuzzyorder

def reduceRenames(prgm, numNames):
	m = findCompatableNames(prgm, numNames)
	return RemapNames(m).walk(prgm)


def collect(d, key, value):
	if not key in d:
		d[key] = value
	else:
		assert d[key] == value

def makeDifferentLUT(diffSet):
	different = {}
	for ng in diffSet:
		for a in ng:
			if not a in different:
				different[a] = set()

			for b in ng:
				if a != b:
					different[a].add(b)
	# Sanity check
##	for ng in diffSet:
##		for a in ng:
##			for b in ng:
##				if a != b:
##					assert b in different[a]
##					assert a in different[b]

	return different

def findCompatableNames(prgm, numNames):
	grr = GetRankedRenames(prgm.relationNames)
	grr.walk(prgm)

	ranks = tuple(reversed(grr.renames.keys()))
	rankedRenames = grr.renames
	diffSet = set(grr.tempTypes.values())
	
	u = PADS.UnionFind.UnionFind()


	different = makeDifferentLUT(diffSet)


	def canUnionRename(rn):
		assert len(set(rn.keys())) == len(rn)

		# Can't eliminate the rename if it's degenerate.
		if len(set(rn.values())) < len(rn):
			return False

		for k, v in rn.iteritems():
			if not canUnionPair(k, v):
				return False
		return True

	def canUnionPair(k, v):
		a = u[k]
		b = u[v]

		if a != b:
			for d in different[b]:
				if u[d] == a:
					return False

			for d in different[a]:
				if u[d] == b:
					return False
		return True


	def doUnionRename(rn):
		for k, v in rn.iteritems():
			doUnionPair(k, v)

	def doUnionPair(k, v):
		a = u[k]
		b = u[v]

		if a != b:
			assert canUnionPair(a, b)
			
			u.union(a, b)

			# Generate the new difference set
			oldDiff = different[a].union(different[b])
			ns = set()
			for d in oldDiff:
				ns.add(u[d])

			assert not a in ns
			assert not b in ns

			different[a] = ns
			different[b] = ns
	
	eliminated = 0
	remaining = []

	for rank in ranks:
		for rn in rankedRenames[rank]:
			if canUnionRename(rn):
				doUnionRename(rn)
				eliminated += 1
			else:
				remaining.append(rn)



	m = createRenameMap(u, numNames)

	allDefs = set(grr.tempTypes.values())
	allDefs.update(grr.relationTypes.values())

	fo = open('renamelut.py', 'w')
	fo.write('data = ')
	fo.write(repr(rankedRenames))
	fo.write('\n')
	fo.write('different = ')
	fo.write(repr(allDefs))
	fo.write('\n')
	fo.write('proposed = ')
	fo.write(repr(m))
	fo.write('\n')
	fo.close()

	if False:
		m = fuzzyorder.remap(rankedRenames, allDefs)

	return m

def createRenameMap(u, numNames):
	m = []
	pool = {}
	newlut = {}
	currentNew = 0
	for i in range(numNames):
		c = u[i]
		
		if not c in newlut:
			newlut[c] = currentNew
			pool[currentNew] = set()
			currentNew += 1

		m.append(newlut[c])
		#m[i] = newlut[c]
		pool[newlut[c]].add(i)

##	# Sanity check
##	different = makeDifferentLUT(diffSet)
##	for n, os in pool.iteritems():
##		for a in os:
##			for b in os:
##				assert not a in different[b]
##				assert not b in different[a]

	return m



def collectNameDomains(fields, names, nameDomains):
	for (fieldname, fielddomain), name  in zip(fields, names):
		if isinstance(name, int):
			collect(nameDomains, name, fielddomain)	
		else:
			collectNameDomains(fielddomain.fields, name, nameDomains)
# HACK duplicated
def flatten(names):
	outp = []
	for n in names:
		if isinstance(n, int):
			outp.append(n)
		else:
			outp.extend(flatten(n))
	return tuple(outp)


def translateNames(names, lut):
	outp = []
	for name in names:
		if isinstance(name, int):
			res = lut[name]
		else:
			res = translateNames(name, lut)
		outp.append(res)
	return tuple(outp)

class GetRankedRenames(StandardVisitor):
	def __init__(self, relationTypes):
		self.renames = {}
		self.groups = set()
		self.rank = 0

		self.relationTypes 	= {}

		self.renameGroup = PADS.UnionFind.UnionFind()
		
		self.nameDomains = {}

		for relation, names in relationTypes.iteritems():
			flat = frozenset(flatten(names))
			self.relationTypes[relation.name] = flat
			
			collectNameDomains(relation.fields, names, self.nameDomains)
			
			for name in flat:
				self.renameGroup.union(name)

		for name, d in self.nameDomains.iteritems():
			assert isinstance(name, int)
			assert isinstance(d, datalogast.Domain)
			
		
		self.tempTypes = {}


	def visitLoad(self, node):
		t = self.relationTypes[node.name]
		self.tempTypes[node.target] = t

	def visitStore(self, node):
		t = self.tempTypes[node.target]
		assert self.relationTypes[node.name] == t, (node.name, self.relationTypes[node.name], t)

	def visitProject(self, node):		
		t = self.tempTypes[node.source]
		assert t.issuperset(node.fields), (t, node.fields)
		t = t-node.fields
		self.tempTypes[node.target] = t

	def visitInvert(self, node):		
		t = self.tempTypes[node.expr]
		self.tempTypes[node.target] = t

	def visitRelProd(self, node):		
		a = self.tempTypes[node.left]
		b = self.tempTypes[node.right]
		t = a.union(b)
		assert t.issuperset(node.fields), (t, node.fields)
		t = t-node.fields
		
		self.tempTypes[node.target] = t

	def visitUnion(self, node):
		a = self.tempTypes[node.left]
		b = self.tempTypes[node.right]
		t = a.union(b)
		self.tempTypes[node.target] = t

	def visitJoin(self, node):
		a = self.tempTypes[node.left]
		b = self.tempTypes[node.right]
		t = a.union(b)
		self.tempTypes[node.target] = t

	def visitRename(self, node):
		lut = node.lut
		self.groups.add(frozenset(lut.keys()))
		self.groups.add(frozenset(lut.values()))

		for k, v in lut.iteritems():
			assert isinstance(k, int)
			assert isinstance(v, int)
			
			assert k in self.nameDomains
			
			if not v in self.nameDomains:
				self.nameDomains[v] = self.nameDomains[k]
			else:
				assert self.nameDomains[v] == self.nameDomains[k]
			
			self.renameGroup.union(k, v)

		if not self.rank in self.renames:
			self.renames[self.rank] = []
		self.renames[self.rank].append(lut)

		# Types
		t = self.tempTypes[node.source]
		t = frozenset([node.lut.get(n, n) for n in t])

		self.tempTypes[node.target] = t


	def visitInstructionBlock(self, node):
		for op in node.instructions:
			self.visit(op)

	def visitLoop(self, node):
		self.rank += 1
		self.visit(node.block)
		self.rank -= 1

	def visitExpression(self, node):
		self.visit(node.block)

	def visitProgram(self, node):
		self.visit(node.body)




class RemapNames(StandardVisitor):
	def __init__(self, m):
		self.m = m
		self.temps = {}

	def visitLoad(self, node):		
		return node.translate(self.temps, self.m)

	def visitStore(self, node):		
		return node.translate(self.temps, self.m)

	def visitRename(self, node):
		node = node.translate(self.temps, self.m)

		if not node.lut:
			self.temps[node.target] = node.source
			return None
		else:
			return node

	def visitProject(self, node):		
		return node.translate(self.temps, self.m)

	def visitUnion(self, node):		
		return node.translate(self.temps, self.m)

	def visitInvert(self, node):
		return node.translate(self.temps, self.m)

	def visitJoin(self, node):
		return node.translate(self.temps, self.m)

	def visitRelProd(self, node):
		return node.translate(self.temps, self.m)
	
	def visitInstructionBlock(self, node):
		rewriten = node.__class__()
		
		for op in node.instructions:
			op = self.visit(op)
			if op:
				rewriten.addInstruction(op)
		return rewriten

	def visitLoop(self, node):
		block = self.visit(node.block)
		if len(block.instructions) == 0:
			# A loop wrapping nothing is pointless.
			return None
		elif len(block.instructions) == 1 and isinstance(block.instructions[0], node.__class__):
			# A loop wrapping a loop is redundant.
			return block.instructions[0]
		else:
			return node.__class__(block)

	def visitExpression(self, node):
		return node.__class__(self.visit(node.block), node.read, node.modify, node.datalog)

	def visitProgram(self, node):
		relationNames = {}
		
		for rel, names in node.relationNames.iteritems():
			assert len(rel.fields) == len(names)
			trans = translateNames(names, self.m)
			assert len(rel.fields) == len(trans)
			relationNames[rel] = trans

		nameDomains = {}

		for oldName in range(len(self.m)):
			newName = self.m[oldName]
			d = node.nameDomains[oldName]
			collect(nameDomains, newName, d)

		# Sanity check: sizes must match
		for rel in node.relations:
			names = relationNames[rel]
			assert len(names) == len(rel.fields), (rel, names)

		return node.__class__(node.domains, node.structures, node.relations, nameDomains, relationNames, self.visit(node.body))
