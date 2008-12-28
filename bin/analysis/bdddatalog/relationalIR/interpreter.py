from __future__ import absolute_import

from util.visitor import StandardVisitor

from .. import relational

import time

from . printprogram import PrintProgram

from .. relational.managerhack import m

import gc

import time

class DependancyExtractor(StandardVisitor):
	def __init__(self):
		self.depends = {}
		self.canDirty = []
		self.renames = []
		self.forgets = set()
		self.expressions = []
		self.profile = []

	def visitLoad(self, node):
		pass

	def visitStore(self, node):
		pass

	def visitUnion(self, node):
		self.profile.append(node)


	def visitJoin(self, node):
		self.profile.append(node)

	
	def visitInvert(self, node):
		self.profile.append(node)


	def visitRelProd(self, node):
		self.forgets.add(node.fields)
		self.profile.append(node)


	def visitProject(self, node):
		self.forgets.add(node.fields)
		self.profile.append(node)

	def visitRename(self, node):
		self.renames.append(node.lut)
		self.profile.append(node)

	def visitInstructionBlock(self, node):
		for op in node.instructions:
			self.visit(op)

	def registerDepend(self, rel, node):
		if not rel in self.depends:
			self.depends[rel] = []
		self.depends[rel].append(node)

	def visitExpression(self, node):
		for read in node.read:
			self.registerDepend(read, node)
		self.canDirty.append(node)
		self.visit(node.block)
		self.expressions.append(node)
		self.profile.append(node)

	def visitLoop(self, node):
		for read in node.read:
			self.registerDepend(read, node)
		self.canDirty.append(node)
		self.visit(node.block)
		self.profile.append(node)


	def visitProgram(self, node):
		self.visit(node.body)

class OutOfTimeError(Exception):
	pass

class Interpreter(StandardVisitor):
	# Logical domain bindings?
	def __init__(self, prgm, domainBindings, domainOrder=None):
		self.prgm = prgm

		# TODO stronger check?
		assert len(domainBindings) >= len(prgm.domains)

		self.domainBindings = domainBindings
		
		self.temporaries = {}


		self.verbose = False
		self.enableProfiling = False

		#self.verbose = True
		#self.enableProfiling = True


		self.domainOrder = domainOrder

		point0 = time.clock()
		self.findDependancies()
		point1 = time.clock()
		self.buildPhysical()
		point2 = time.clock()
		self.makeRelations()
		point3 = time.clock()
		self.makeOperators()
		point4 = time.clock()

		#print point1-point0, point2-point1, point3-point2, point4-point3

		self.maximumTime = 0.0

		# Different analysis stages? FI/FS?	

	def findDependancies(self):
		de = DependancyExtractor()
		de.walk(self.prgm)
		
		# Setup depenancies.
		self.depends = de.depends
		self.dirty = {}
		for node in de.canDirty:
			self.dirty[node] = False

		self.forgets = de.forgets
		self.renames = de.renames

		self.expressions = de.expressions
		self.profile 	= set(de.profile)

	def getPhysical(self, fields, names):
		attr = []
		for (fieldname, fielddomain), name in zip(fields, names):
			if isinstance(name, (tuple, list)):
				res = relational.PhysicalStructure(fielddomain.name, self.getPhysical(fielddomain.fields, name))
			else:
				res = self.physical[name]

			attr.append((fieldname, res))
		return tuple(attr)

	def buildPhysical(self):
		if False:
			self.newBuildPhysical()
		else:
			self.oldBuildPhysical()

	def newBuildPhysical(self):
		self.logical = {}

		# Make the logical domains
		for name, rng in self.domainBindings.iteritems():
			self.logical[name] = relational.LogicalDomain(name, rng)		

		# Calculate the total number of bits required.
		totalbits = 0
		for name, domain in self.prgm.nameDomains.iteritems():
			assert domain.name in self.logical, (domain, self.logical)
			totalbits += self.logical[domain.name].numbits

		# Ensure alloctaion.
		for i in range(totalbits):
			m.IthVar(i)

		# Make the physical domains.
		self.physical = {}

		domainIDs = sorted(self.prgm.nameDomains.iterkeys())

		print "Grouping"
		groups = []
		last = None
		for domainID in domainIDs:
			domain = self.prgm.nameDomains[domainID]			
			logical = self.logical[domain.name]

			if logical == last:
				groups[-1].append(domainID)
			else:
				groups.append([domainID])
			
			last = logical
		

		print "Allocating bits"

		# Allocate the physical domains
		currentbit = 0
		for group in groups:
			domain = self.prgm.nameDomains[group[0]]			
			logical = self.logical[domain.name]
			logicalcurrent = currentbit
			logicalstride = len(group)

			for domainID in group:
				self.physical[domainID] = logical.physical(logicalcurrent, logicalstride)
				logicalcurrent += 1
				currentbit += logical.numbits

		print "Done Physical"


		assert currentbit == totalbits

	def oldBuildPhysical(self):
		self.logical = {}
		self.binned = {}

		# Make the logical domains
		for name, rng in self.domainBindings.iteritems():
			self.logical[name] = relational.LogicalDomain(name, rng)
			self.binned[name] = []		

		totalbits = 0

		if self.domainOrder:
			domainOrder = self.domainOrder
		else:
			domainOrder = self.logical.keys()

		#print "!!!!!!", self.prgm.nameDomains
		#assert False


		# Heuristic: Group the names according the their logical domain.
		for name, domain in self.prgm.nameDomains.iteritems():
			assert domain.name in self.logical, (domain, self.logical)
			self.binned[domain.name].append(name)
			totalbits += self.logical[domain.name].numbits

		if self.verbose:
			print "Num bits: %d" % totalbits

		# Make sure the variables are allocated
		for i in range(totalbits):
			m.IthVar(i)

		# Make the physical domains.
		self.physical = {}

		# Allocate the physical domains
		currentbit = 0
		for domainName in domainOrder:
			names = self.binned[domainName]
			logical = self.logical[domainName]
			logicalcurrent = currentbit
			logicalstride = len(names)

			# Interleave domains of the same type.
			for name in names:
				self.physical[name] = logical.physical(logicalcurrent, logicalstride)
				logicalcurrent += 1
				currentbit += logical.numbits

		assert currentbit == totalbits

		# TODO cache renames, and forgets

	def makeRelations(self):
		self.relations = {}
		
		# Make the relations.
		for relation, names in self.prgm.relationNames.iteritems():
			attr = self.getPhysical(relation.fields, names)
			r = relational.Relation(attr)
			self.relations[relation.name] = r

	def makeOperators(self):
		for d in self.prgm.domains:
			for op, relation in d.ops.iteritems():
				self.makeOperation(op, self.relations[relation.name])

		for d in self.prgm.structures:
			for op, relation in d.ops.iteritems():
				self.makeOperation(op, self.relations[relation.name])

	def makeOperation(self, op, relation):
		assert len(relation.attributes) == 2
		a = relation.attributes[0][1]
		b = relation.attributes[1][1]
		relation.data = a.makeCompare(op, b)
		
	def set(self, name, *args, **kargs):
		mask = (self.relations[name].entry(*args, **kargs)).data
		rel = self.loadRelation(name)
		result = rel | mask
		self.storeRelation(name, result) # Will mark dirty?

	def setFlat(self, name, flat):
		assert isinstance(flat, (list, tuple)), flat
		mask = self.relations[name].encoder.encode(flat)
		rel = self.loadRelation(name)
		result = rel | mask
		self.storeRelation(name, result) # Will mark dirty?
			
	def execute(self):
		gc.collect() # Just to be sure, for performance measurement.
		
		self.callCount 	= {}
		self.timeElapsed = {}

		for n in self.profile:
			self.callCount[n] = 0
			self.timeElapsed[n] = 0
		
		self.start = time.clock()
		self.walk(self.prgm)
		elapsed = time.clock()-self.start

		if self.enableProfiling: self.dumpProfile()
		#Program(anno).walk(self.prgm, '')
	
		return elapsed
	
	def dumpProfile(self):
		stats = []

		for e in self.expressions:
			stats.append((e, self.callCount[e], self.timeElapsed[e]))

		anno = {}
		for node in self.profile:
			anno[node] = self.timeElapsed[node]*1000.0

		stats.sort(key=lambda e: e[2], reverse=True)

		print "===== Profile ====="
		for e, count, etime in stats[:5]:
			print count, etime*1000.0
			print e.datalog
			print
			PrintProgram(anno).walk(e, '')
			print

		print "GC Time:", m.ReadGarbageCollectionTime()
		print "RO Time:", m.ReadReorderingTime()

		print "Size:", m.ReadSize()

		print "Slots size:", m.ReadSlots()
		print "Slots used:", m.ReadUsedSlots()

		print "Cache size:", m.ReadCacheSlots()
		print "Cache used:", m.ReadCacheUsedSlots()

		print "Cache Hit Rate: %.2f%%" % ((m.ReadCacheHits()/m.ReadCacheLookUps())*100)


	def markDirty(self, name):
		if name in self.depends:
			for dep in self.depends[name]:
				self.dirty[dep] = True

	def loadRelation(self, name):
		return self.relations[name].data

	def storeRelation(self, name, data):
		old = self.relations[name].data

		if data != old:
			self.relations[name].data = data
			self.markDirty(name)

	def visitLoad(self, node):
		rel = self.loadRelation(node.name)
		self.temporaries[node.target] = rel

	def visitStore(self, node):
		data = self.temporaries[node.target]
		self.storeRelation(node.name, data)

	def visitUnion(self, node):
		left = self.temporaries[node.left]
		right = self.temporaries[node.right]
		result = left|right
		self.temporaries[node.target] = result
		
	def visitInvert(self, node):
		expr = self.temporaries[node.expr]
		result = ~expr
		self.temporaries[node.target] = result

	def visitJoin(self, node):
		left = self.temporaries[node.left]
		right = self.temporaries[node.right]
		result = left&right
		self.temporaries[node.target] = result


	def visitRelProd(self, node):
		left = self.temporaries[node.left]
		right = self.temporaries[node.right]
		forget = relational.util.forget(relational.m, [self.physical[name] for name in node.fields])
		
		result = left.AndAbstract(right, forget)
		
		self.temporaries[node.target] = result

	def visitProject(self, node):
		source = self.temporaries[node.source]
		forget = relational.util.forget(relational.m, [self.physical[name] for name in node.fields])
		
		result = source.ExistAbstract(forget)
		
		self.temporaries[node.target] = result

	def visitRename(self, node):
		plut = {}

		for k, v in node.lut.iteritems():
			plut[self.physical[k]] = self.physical[v]
		p = relational.util.permutation(relational.m, plut)

		source = self.temporaries[node.source]
		result = source.Permute(p)
		self.temporaries[node.target] = result

	def visitInstructionBlock(self, node):
		for op in node.instructions:
			self.process(op)

	def visitExpression(self, node):
		if self.dirty[node]:			
			if self.verbose:
				print "Processing", node.datalog
			
			self.dirty[node] = False
			self.process(node.block)

			#self.temporaries = {}


	def visitLoop(self, node):
		while self.dirty[node]:
			self.dirty[node] = False
			self.process(node.block)

	def visitProgram(self, node):
		self.process(node.body)


	def process(self, node):
		if 0.0 < self.maximumTime  and self.maximumTime < (time.clock()-self.start):
			raise OutOfTimeError
		
		if self.enableProfiling and node in self.profile:
			start = time.clock()

		self.visit(node)

		if self.enableProfiling and node in self.profile:
			self.timeElapsed[node] += time.clock()-start
			self.callCount[node] += 1

