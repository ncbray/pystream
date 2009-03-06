from __future__ import absolute_import

# The model for the analysis

from . model import canonical

#from . import regionanalysis
from . import transferfunctions
from . import constraintbuilder
from . import dataflow


class RegionBasedShapeAnalysis(object):
	def __init__(self, extractor, db):
		self.extractor   = extractor
		self.canonical   = canonical.CanonicalObjects()
		self.worklist    = dataflow.Worklist()
		self.environment = dataflow.DataflowEnvironment()

		self.constraintbuilder = constraintbuilder.ShapeConstraintBuilder(self, self.processCode)

		self.db = db


		self.pending = set()
		self.visited = set()

	def process(self, trace=False):
		self.worklist.process(self, trace)

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
		self.process(trace=True)

		for i, arg in enumerate(args):
			self.bindExisting(arg, i, callPoint)
			self.process(trace=True)

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
				self.process()

			print

	def dumpStatistics(self):
		print "Entries:", len(self.environment._secondary)
		print "Unique Config:", len(self.canonical.configurationCache)
		print "Max Worklist:", self.worklist.maxLength
		print "Steps:", "%d/%d" % (self.worklist.usefulSteps, self.worklist.steps)

import collections
def evaluate(console, extractor, result, entryPoints):
	console.begin('shape analysis')

	#regionLUT = regionanalysis.evaluate(extractor, entryPoints, db)

	rbsa = RegionBasedShapeAnalysis(extractor, result)

	for code, selfobj, args in entryPoints:
		rbsa.addEntryPoint(code, selfobj, args)

	#rbsa.handleAllocations()

	rbsa.dumpStatistics()

	lut = collections.defaultdict(set)
	for point, context, index in sorted(rbsa.environment._secondary.keys()):
		#if index.currentSet.containsParameter(): continue
		lut[index.object].add((point[0], index.currentSet, index.externalReferences))

	for obj, indexes in lut.iteritems():
		print obj
		for index in sorted(indexes):
			if index[1] and index[1].radius:
				print '\t', index
		print

	console.end()