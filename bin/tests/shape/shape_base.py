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

from __future__ import absolute_import

import unittest

import time

import collections

import analysis.shape

from language.python import ast
from analysis.storegraph import storegraph, canonicalobjects, setmanager

import application.context
import decompiler.programextractor

from util.tvl import *

class MockInformationProvider(object):
	def __init__(self, sys):
		self.sys = sys

	def loadSlotName(self, node):
		return (node.fieldtype, node.name.object)

	def storeSlotName(self, node):
		return (node.fieldtype, node.name.object)

	def indexSlotName(self, lcl, i):
		return ('Array', self.sys.extractor.getObject(i))

class TestConstraintBase(unittest.TestCase):
	def setUp(self):
		compiler = application.context.CompilerContext(None)
		self.extractor = decompiler.programextractor.Extractor(compiler)
		compiler.extractor = self.extractor

		cpacanonical = canonicalobjects.CanonicalObjects()
		self.sys  = analysis.shape.RegionBasedShapeAnalysis(self.extractor, cpacanonical, MockInformationProvider(self))
		self.root = storegraph.StoreGraph(self.extractor, cpacanonical)

		self.setInOut((None, 0), (None, 1))

		self.shapeSetUp()

	def existing(self, obj):
		return ast.Existing(self.extractor.getObject(obj))

	def shapeSetUp(self):
		raise NotImplementedError

	def refs(self, *args):
		return self.sys.canonical.refs(*args)

	def expr(self, *args):
		return self.sys.canonical.expr(*args)

	def makeLocalObjs(self, name):
		lcl = ast.Local(name)
		slot = self.sys.canonical.localSlot(lcl)
		expr = self.sys.canonical.localExpr(slot)
		return lcl, slot, expr

	def parameterSlot(self, index):
		assert isinstance(index, int), index
		return self.sys.canonical.localSlot(index)

	def hitsFromRC(self, index):
		hits = []
		for slot in index.radius:
			if slot.isLocal():
				hits.append(self.sys.canonical.localExpr(slot))
		return hits

	def convert(self, row, entry):
		type_  = None
		region = None

		if len(row) == 3:
			current, hits, misses = row
		else:
			current, hits, misses, unknowns = row

		hits     = frozenset(hits if hits is not None else ())
		misses   = frozenset(misses if misses is not None else ())
		external = False

		hits = hits.union(self.hitsFromRC(current))

		externalReferences = False
		allocated = False
		index = self.sys.canonical.configuration(type_, region, entry, current, externalReferences, allocated)
		paths = self.sys.canonical.paths(hits, misses)
		secondary = self.sys.canonical.secondary(paths, external)
		return index,secondary

	def match(self, entrySet, point, index):
		return point == self.outputPoint and index.entrySet == entrySet and not index.externalReferences

	def countOutputs(self, entrySet):
		count = 0
		for point, context, index in self.sys.environment._secondary.iterkeys():
			if self.match(entrySet, point, index):
				count += 1
		return count

	def dumpOutputs(self, entrySet):
		print
		print "DUMP"
		for (point, context, index), secondary in self.sys.environment._secondary.iteritems():
			if self.match(entrySet, point, index):
				print ">"*40
				self.dumpData(index, secondary)
				print "<"*40
				print


	def setInOut(self, inp, outp):
		self.inputPoint = inp
		self.outputPoint = outp

	def setConstraint(self, constraint):
		self.constraint = constraint
		self.setInOut(constraint.inputPoint, constraint.outputPoint)

	def checkTransfer(self, argument, results):
		inputPoint = self.inputPoint
		outputPoint = self.outputPoint
		context = None

		entry = argument[0]
		conf, secondary = self.convert(argument, entry)


		start = time.clock()
		self.sys.environment.merge(self.sys, inputPoint, context, conf, secondary)
		self.sys.process()
		self.elapsed = time.clock()-start

		# Don't check anything... used for debugging
		if results is None: return

		try:
			for row in results:
				econf, esecondary = self.convert(row, entry)

				secondary = self.sys.environment.secondary(outputPoint, context, econf)

				self.assertNotEqual(secondary, None, "Expected output %r not found." % econf)

				if len(row) == 3:
					current, hits, misses = row
					unknowns = None
				else:
					current, hits, misses, unknowns = row

				if hits:
					for e in hits:
						self.assertEqual(secondary.paths.hit(e), TVLTrue, "%r should be a hit." % e)

				if misses:
					for e in misses:
						self.assertEqual(secondary.paths.hit(e), TVLFalse, "%r should be a miss." % e)

				if unknowns:
					for e in unknowns:
						self.assertEqual(secondary.paths.hit(e), TVLMaybe, "%r should be unknown." % e)

		except AssertionError:
			if secondary:
				print
				print "DUMP"
				print econf
				print
				secondary.paths.dump()
				print
			else:
				self.dumpOutputs(entry)
			raise

		try:
			self.assertEqual(self.countOutputs(entry), len(results))
		except AssertionError:
			self.dumpOutputs(entry)
			raise

	def dumpData(self, conf, secondary):
		print conf.object, conf.region
		print conf.entrySet
		print conf.currentSet
		print "external", conf.externalReferences
		print
		print "PATHS"
		print
		secondary.paths.dump()
		print "externalReferences: %r" % secondary.externalReferences

	def dumpPoint(self, givenPoint):
		mapping = self.sys.environment._secondary

		count = 0

		for (point, context, conf), secondary in mapping.iteritems():
			if point != givenPoint: continue
			self.dumpData(conf, secondary)
			print "|%s|" % ("="*80)
			print

			count += 1

		print "%d configurations at point." % count
		print

	def dumpStatistics(self):
		self.sys.dumpStatistics()
#		print "Entries:", len(self.sys.environment._secondary)
#		print "Unique Config:", len(self.sys.canonical.configurationCache)
#		print "Max Worklist:", self.sys.worklist.maxLength
#		print "Steps:", "%d/%d" % (self.sys.worklist.usefulSteps, self.sys.worklist.steps)


	def dump(self, point=None):
		if point is None:
			point = self.outputPoint
		print
		print "/%s\\" % ("*"*80)
		print point
		print
		self.dumpPoint(point)
		self.dumpStatistics()
		if self.elapsed < 1.0:
			print "Time: %.1f ms" % (self.elapsed*1000.0)
		elif self.elapsed < 10.0:
			print "Time: %.2f s" % (self.elapsed)
		else:
			print "Time: %.1f s" % (self.elapsed)
		print "\\%s/" % ("*"*80)
		print


class TestCompoundConstraintBase(TestConstraintBase):
	def makeConstraints(self, func):
		builder = self.sys.constraintbuilder
		builder.process(func)
		return builder.statementPre[func], builder.statementPost[func]

	def statementPre(self, op):
		return self.sys.constraintbuilder.statementPre[op]

	def statementPost(self, op):
		return self.sys.constraintbuilder.statementPost[op]


	def createInput(self, ref):
		entry = ref if self.cs else None
		argument = (ref, None, None)
		conf, secondary = self.convert(argument, entry)
		self.setInput(conf, secondary)

	def setInput(self, conf, secondary):
		self.sys.environment.merge(self.sys, self.inputPoint, self.context, conf, secondary)
