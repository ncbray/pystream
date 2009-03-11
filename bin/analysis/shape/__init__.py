from __future__ import absolute_import

# The model for the analysis

from . model import canonical

from . import regionanalysis
from . import transferfunctions
from . import constraintbuilder
from . import dataflow

class HeapInformationProvider(object):
	def __init__(self, sys, regions):
		self.sys = sys
		self.regions = regions

	def loadSlotName(self, node):
		return node.annotation.reads[0][0]
		#return (node.fieldtype, node.name.object)

	def storeSlotName(self, node):
		return node.annotation.modifies[0][0]
		#return (node.fieldtype, node.name.object)

	def indexSlotName(self, lcl, i):
		iobj = self.sys.extractor.getObject(i)
		fieldName = self.sys.canonical.fieldName('Array', iobj)
		for ref in lcl.annotation.references[0]:
			return ref.field(self.sys, fieldName, ref.region.group.regionHint)
		#return fieldName


class RegionBasedShapeAnalysis(object):
	def __init__(self, extractor, db, info):
		self.extractor   = extractor
		self.canonical   = canonical.CanonicalObjects()
		self.worklist    = dataflow.Worklist()
		self.environment = dataflow.DataflowEnvironment()

		self.constraintbuilder = constraintbuilder.ShapeConstraintBuilder(self, self.processCode)

		self.db   = db
		self.info = info


		self.pending = set()
		self.visited = set()

		self.limit = 20000

		self.aborted = set()

	def process(self, trace=False, limit=0):
		success = self.worklist.process(self, trace, limit)
		if not success:
			print
			print "ITERATION LIMIT HIT"
			self.worklist.worklist[:] = []
		return success

	def setTypePointer(self, obj):
		# HACK for test harnesses.
		pass

	def processCode(self, code):
		if code not in self.visited:
			self.pending.add(code)
			self.visited.add(code)


	def build(self):
		while self.pending:
			current = self.pending.pop()
			print "BUILD", current
			self.constraintbuilder.process(current)


	def addEntryPoint(self, code, selfobj, args):
		self.processCode(code)

		callPoint = self.constraintbuilder.codeCallPoint(code)

		self.build()

		# TODO generate all possible aliasing configuraions?
		self.bindExisting(selfobj, 'self', callPoint)
		sucess = self.process(trace=True)
		if not sucess: self.aborted.add(selfobj)

		for i, arg in enumerate(args):
			self.bindExisting(arg, i, callPoint)
			sucess = self.process(trace=True, limit=self.limit)
			if not sucess: self.aborted.add(arg)


	def bindExisting(self, obj, p, callPoint):
		slot = self.canonical.localSlot(p)
		expr = self.canonical.localExpr(slot)
		refs = self.canonical.refs(slot)


		type_ = self.db.canonical.externalType(obj)
		region = None
		entry = refs
		current = refs
		externalReferences = True
		allocated = False

		hits = (expr,)
		misses = ()

		index     = self.canonical.configuration(type_, region, entry, current, externalReferences, allocated)
		paths     = self.canonical.paths(hits, misses)
		secondary = self.canonical.secondary(paths, externalReferences)


		print
		print "BIND"
		print callPoint
		print index
		print secondary
		print

		self.environment.merge(self, callPoint, None, index, secondary)

	def handleAllocations(self):
		for (code, op), (point, target) in self.constraintbuilder.allocationPoint.iteritems():
			print code
			print op
			print '\t', point
			print '\t', target

			slot = self.canonical.localSlot(target)
			expr = self.canonical.localExpr(slot)
			refs = self.canonical.refs(slot)

			for obj in op.annotation.allocates[0]:
				print '\t\t', obj

				type_   = obj
				region  = None
				entry   = refs
				current = refs
				externalReferences = False
				allocated = True

				hits   = (expr,)
				misses = ()

				index     = self.canonical.configuration(type_, region, entry, current, externalReferences, allocated)
				paths     = self.canonical.paths(hits, misses)
				secondary = self.canonical.secondary(paths, externalReferences)

				self.environment.merge(self, point, None, index, secondary)
				sucess = self.process(trace=True, limit=self.limit)
				if not sucess: self.aborted.add(obj)


			print

	def dumpStatistics(self):
		print "Entries:", len(self.environment._secondary)
		print "Unique Config:", len(self.canonical.configurationCache)
		print "Max Worklist:", self.worklist.maxLength
		print "Steps:", "%d/%d" % (self.worklist.usefulSteps, self.worklist.steps)

import collections
def evaluate(console, extractor, result, entryPoints):
	console.begin('shape analysis')

	regions = regionanalysis.evaluate(extractor, entryPoints, result)

	rbsa = RegionBasedShapeAnalysis(extractor, result, HeapInformationProvider(result, regions))

	for code, selfobj, args in entryPoints:
		rbsa.addEntryPoint(code, selfobj, args)

	rbsa.handleAllocations()

	rbsa.dumpStatistics()

	lut = collections.defaultdict(set)
	for point, context, index in sorted(rbsa.environment._secondary.keys()):
		#if index.currentSet.containsParameter(): continue
		if index.object in rbsa.aborted: continue
		lut[index.object].add((point[0], index.currentSet))

	for obj, indexes in lut.iteritems():
		print obj
		prevCode = None
		for code, rc in sorted(indexes):
			if rc and not rc.containsParameter():
				if prevCode != code:
					print '\t', code
					prevCode = code

				print '\t\t', rc
		print

	print
	print "ABORTED"
	for obj in rbsa.aborted:
		print '\t', obj

	print
	rbsa.dumpStatistics()

	console.end()