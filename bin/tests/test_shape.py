from __future__ import absolute_import

import unittest

import analysis.shape

from programIR.python import ast

import collections

class MockDB(object):
	def __init__(self):
		self.invokeLUT = collections.defaultdict(set)

	def addInvocation(self, function, context, op, dstfunc, dstcontext):
		self.invokeLUT[(function, context, op)].add((dstfunc, dstcontext))


	def invocations(self, function, context, op):
		return self.invokeLUT[(function, context, op)]

class TestConstraintBase(unittest.TestCase):
	def scalarIncrement(self, rc, slot):
		next = self.sys.canonical.incrementRef(rc, slot)
		self.assertEqual(len(next), 1)
		return next[0]	

	def makeLocalObjs(self, name):
		lcl = ast.Local(name)
		slot = self.sys.canonical.localSlot(lcl)
		expr = self.sys.canonical.localExpr(slot)
		return lcl, slot, expr


	def convert(self, row, entry):
		type_  = None
		region = None
		current, hits, misses = row
		if isinstance(hits, tuple): hits = set(hits)
		if isinstance(misses, tuple): misses = set(misses)
		external = False
		
		return self.sys.canonical.configuration(type_, region, entry, current), self.sys.canonical.secondary(hits, misses, external)

	def countOutputs(self):
		count = 0
		for point, context, index in self.sys.environment._secondary.iterkeys():
			if point == self.outputPoint:
				count += 1
		return count
	
	def checkConstraint(self, argument, results):
		inputPoint = self.constraint.inputPoint
		outputPoint = self.constraint.outputPoint
		context = None

		entry = argument[0]
		conf, secondary = self.convert(argument, entry)


		self.sys.environment.merge(self.sys, inputPoint, context, conf, secondary)
		self.sys.process()

		self.assertEqual(self.countOutputs(), len(results))

		for row in results:
			econf, esecondary = self.convert(row, entry)
			secondary = self.sys.environment.secondary(outputPoint, context, econf)

			self.assertNotEqual(secondary, None)
			self.assertEqual(secondary.hits, esecondary.hits)
			self.assertEqual(secondary.misses, esecondary.misses)	

class TestExpressions(unittest.TestCase):
	def setUp(self):
		self.db = MockDB()
		self.sys  = analysis.shape.RegionBasedShapeAnalysis(self.db)

		self.fielda = self.sys.canonical.fieldSlot(None, 'a')
		self.fieldb = self.sys.canonical.fieldSlot(None, 'b')

		self.localz = self.sys.canonical.localSlot('zero')
		self.localo = self.sys.canonical.localSlot('one')

		self.zero = self.sys.canonical.localExpr(self.localz)
		self.zero_a = self.sys.canonical.fieldExpr(self.zero,   self.fielda)
		self.zero_a_a = self.sys.canonical.fieldExpr(self.zero_a, self.fielda)
		self.zero_a_b = self.sys.canonical.fieldExpr(self.zero_a, self.fieldb)

		self.zero_b = self.sys.canonical.fieldExpr(self.zero,   self.fieldb)
		self.zero_b_a = self.sys.canonical.fieldExpr(self.zero_b, self.fielda)
		self.zero_b_b = self.sys.canonical.fieldExpr(self.zero_b, self.fieldb)

		self.one = self.sys.canonical.localExpr(self.localo)		
		self.one_a = self.sys.canonical.fieldExpr(self.one,   self.fielda)
		self.one_a_a = self.sys.canonical.fieldExpr(self.one_a, self.fielda)
		self.one_a_b = self.sys.canonical.fieldExpr(self.one_a, self.fieldb)
		
		self.one_b = self.sys.canonical.fieldExpr(self.one,   self.fieldb)
		self.one_b_a = self.sys.canonical.fieldExpr(self.one_b,   self.fielda)
		self.one_b_b = self.sys.canonical.fieldExpr(self.one_b,   self.fieldb)

		self.allExpr = set((self.zero, self.zero_a, self.zero_a_b, self.one, self.one_a, self.one_a_b))

	def testLocalSubLocal(self):
		# A valid sub
		mlcl0 = self.zero.substitute(self.sys, self.zero, self.one)
		self.assertEqual(mlcl0, self.one)

		# An invalid sub
		mlcl0 = self.zero.substitute(self.sys, self.one, self.zero)
		self.assertEqual(mlcl0, None)


	def testFieldSubLocal(self):
		# A valid sub
		mexpr00 = self.zero_a.substitute(self.sys, self.zero, self.one)
		self.assertEqual(mexpr00, self.one_a)

		# An invalid sub
		mexpr00 = self.zero_a.substitute(self.sys, self.one, self.zero)
		self.assertEqual(mexpr00, None)

	def testFieldSubField(self):
		# A valid sub
		mexpr01 = self.zero_a_b.substitute(self.sys, self.zero_a, self.one_a)
		self.assertEqual(mexpr01, self.one_a_b)

		# An invalid sub
		mexpr01 = self.zero_a_b.substitute(self.sys, self.one_a, self.zero_a)
		self.assertEqual(mexpr01, None)

	def testSubUpdate(self):
		exprs = set((self.zero_a_b, self.one_a))
		expected = set((self.zero_a_b, self.one_a, self.one_a_b))

		analysis.shape.transferfunctions.substituteUpdate(self.sys, exprs, self.zero, self.one)

		self.assertEqual(exprs, expected)	



	def testFilterUnstable1(self):
		stableValues = frozenset()
		result = analysis.shape.transferfunctions.filterUnstable(self.sys, self.allExpr, self.localz, stableValues)

		expected = set((self.one, self.one_a, self.one_a_b))
		self.assertEqual(result, expected)

# No Longer quite right
##	def testFilterUnstable2(self):
##		# Preserve location stable
##		result = analysis.shape.transferfunctions.filterUnstable(self.sys, self.allExpr, self.localz, True)
##
##		expected = set((self.zero, self.one, self.one_a, self.one_a_b))
##		self.assertEqual(result, expected)


	def testFilterUnstable3(self):
		# Preserve location stable
		stableValues = frozenset()
		result = analysis.shape.transferfunctions.filterUnstable(self.sys, self.allExpr, self.fielda, stableValues)

		expected = set((self.zero, self.one))
		self.assertEqual(result, expected)

# No longer quite right
##	def testFilterUnstable4(self):
##		# Preserve location stable
##		stableValues = frozenset()
##		result = analysis.shape.transferfunctions.filterUnstable(self.sys, self.allExpr, self.fielda, stableValues)
##		
##		expected = set((self.zero, self.one, self.zero_a, self.one_a))
##		self.assertEqual(result, expected)


	def testFilterUnstable5(self):
		# Preserve location stable
		stableValues = frozenset()
		result = analysis.shape.transferfunctions.filterUnstable(self.sys, self.allExpr, self.fieldb, stableValues)

		expected = set((self.zero, self.one, self.zero_a, self.one_a))
		self.assertEqual(result, expected)

	def testFilterUnstable6(self):
		# Preserve location stable
		stableValues = frozenset((self.zero_a_b, self.one_a_b))
		result = analysis.shape.transferfunctions.filterUnstable(self.sys, self.allExpr, self.fieldb, stableValues)
		
		expected = self.allExpr
		self.assertEqual(result, expected)



	def testUpdateHitMiss1(self):
		# zero = zero.a
		e0, e1 =  self.zero, self.zero_a

		# How do we know self.zero_a != self.zero_a_b?

		slot = e0.slot
		hits   = set((self.zero_a_b,))
		misses = set((self.one_a_b, self.zero_a_a))
		b0 = False
		b1 = False

		newHits, newMisses = analysis.shape.transferfunctions.updateHitMiss(self.sys, e0, e1, b0, b1, slot, hits, misses)

		# The retargeted hit
		# HACK
		#expectedHits   = set((self.zero_b,))
		expectedHits   = set()

		# This original miss is not disrupted, and as the configuration does not alias to e1, it must now miss e0
		# HACK precision lost if RHS and LHS conflict
		# TODO improve precision
		#expectedMisses = set((self.one_a_b, self.zero_a))
		expectedMisses = set((self.one_a_b,))

		
		self.assertEqual(newHits, expectedHits)
		self.assertEqual(newMisses, expectedMisses)
		

	def testUpdateHitMiss2(self):
		# zero = zero.a
		e0 =  self.zero
		e1 =  self.zero_a
		slot = e0.slot
		hits   = set((self.zero_a_b,))
		misses = set((self.one_a_b,))
		b0 = False
		b1 = True

		newHits, newMisses = analysis.shape.transferfunctions.updateHitMiss(self.sys, e0, e1, b0, b1, slot, hits, misses)

		# HACK precision lost if RHS and LHS conflict
		#expectedHits = set((self.zero_b,))
		# TODO improve precision
		expectedHits = set()
		expectedMisses = set((self.one_a_b,))

		self.assertEqual(newHits, expectedHits)
		self.assertEqual(newMisses, expectedMisses)


	def testUpdateHitMiss3(self):
		# zero = zero.a
		e0 =  self.zero
		e1 =  self.zero_a
		slot = e0.slot
		hits   = set((self.zero_a_b,))
		misses = set((self.one_a_b,))
		b0 = True
		b1 = False

		newHits, newMisses = analysis.shape.transferfunctions.updateHitMiss(self.sys, e0, e1, b0, b1, slot, hits, misses)

		# HACK precision lost if RHS and LHS conflict
		#expectedHits = set((self.zero, self.zero_b))
		# TODO improve precision
		expectedHits = set()
		expectedMisses = set((self.one_a_b,))

		self.assertEqual(newHits, expectedHits)
		self.assertEqual(newMisses, expectedMisses)


class TestReferenceCounts(unittest.TestCase):
	def setUp(self):
		self.db = MockDB()
		self.sys  = analysis.shape.RegionBasedShapeAnalysis(self.db)

		self.fielda = self.sys.canonical.fieldSlot(None, 'a')
		self.fieldb = self.sys.canonical.fieldSlot(None, 'b')

		self.localz = self.sys.canonical.localSlot('zero')
		self.localo = self.sys.canonical.localSlot('one')

	def scalarIncrement(self, rc, slot):
		next = self.sys.canonical.incrementRef(rc, slot)
		self.assertEqual(len(next), 1)
		return next[0]	

	def testIncrementSaturate(self):
		current = None

		# HACK to get the refcount k
		for i in range(self.sys.canonical.rcm.k+1):
			next = self.scalarIncrement(current, self.localz)

			self.assertNotEqual(current, next)

			self.assertEqual(len(next.counts), 1)
			slot, count = tuple(next.counts)[0]
			self.assertEqual(slot, self.localz)
			self.assertEqual(count, i+1)
			
			current = next
	
		next = self.scalarIncrement(current, self.localz)
		self.assertEqual(current, next)

	def testDecrement(self):
		current = None

		inc1 = self.scalarIncrement(None, self.localz)
		inc2 = self.scalarIncrement(inc1, self.localz)
		inc3 = self.scalarIncrement(inc2, self.localz)

		# Decrementing infinity can yield two different configurations
		dec2 = self.sys.canonical.decrementRef(inc3, self.localz)		
		self.assertEqual(set(dec2), set((inc2,inc3)))

		# Decrementing an "intermediate" value will result in a single 
		dec1 = self.sys.canonical.decrementRef(inc2, self.localz)
		self.assertEqual(dec1, (inc1,))

		# Decrementing one can eliminate the reference count
		dec0 = self.sys.canonical.decrementRef(inc1, self.localz)
		self.assertEqual(dec0, ())



##class TestForgetConstraint(TestConstraintBase):
##	def setUp(self):
##		self.sys  = analysis.shape.RegionBasedShapeAnalysis()
##
##		self.aLcl, self.aSlot, self.aExpr  = self.makeLocalObjs('a')
##		self.bLcl, self.bSlot, self.bExpr  = self.makeLocalObjs('b')
##		self.cLcl, self.cSlot, self.cExpr  = self.makeLocalObjs('c')
##		self.xAttr = self.sys.canonical.fieldSlot(None, 'x')
##
##		self.axExpr = self.sys.canonical.fieldExpr(self.aExpr, self.xAttr)
##		self.bxExpr = self.sys.canonical.fieldExpr(self.bExpr, self.xAttr)
##		self.cxExpr = self.sys.canonical.fieldExpr(self.cExpr, self.xAttr)
##
##
##		self.aRef = self.scalarIncrement(None, self.aSlot)
##		self.bRef = self.scalarIncrement(None, self.bSlot)
##		self.cRef = self.scalarIncrement(None, self.cSlot)
##
##		self.abRef = self.scalarIncrement(self.aRef, self.bSlot)
##		self.bcRef = self.scalarIncrement(self.bRef, self.cSlot)
##
##		self.axRef = self.scalarIncrement(self.aRef, self.xAttr)
##		self.bxRef = self.scalarIncrement(self.bRef, self.xAttr)
##		self.cxRef = self.scalarIncrement(self.cRef, self.xAttr)
##
##
##		dataflow = analysis.shape.dataflow
##		self.entryShape = dataflow.DataflowStore()
##		self.exitShape  = dataflow.DataflowStore()
##
##
##		self.inputPoint = 0
##		self.outputPoint = 1
##
##		# b = a
##		self.constraint = analysis.shape.constraints.ForgetConstraint(self.inputPoint, self.outputPoint, self.aExpr, self.bExpr)
##		self.constraint.connect(self.entryShape, self.exitShape)
##
##	def testRemember(self):
##		# c -> c
##
##		argument = (self.cRef, (self.axExpr,), None)
##		results = [
##			(self.cRef, None, None),
##			]
##		self.checkConstraint(argument, results)
##
##
##	def testForget(self):
##		# a -> nil
##
##		argument = (self.aRef, None, None)
##		results = [
##			]
##		self.checkConstraint(argument, results)


class TestCopyConstraint(TestConstraintBase):
	def setUp(self):
		self.db = MockDB()
		self.sys  = analysis.shape.RegionBasedShapeAnalysis(self.db)
		
		self.cLcl, self.cSlot, self.cExpr  = self.makeLocalObjs('c')
		self.cRef = self.scalarIncrement(None, self.cSlot)

		self.inputPoint  = 0
		self.outputPoint = 1

		# b = a
		self.constraint = analysis.shape.constraints.CopyConstraint(self.sys, self.inputPoint, self.outputPoint)


	def testNoAlias(self):
		# c -> c

		argument = (self.cRef, None, None)
		results = [
			(self.cRef, None, None),
			]
		self.checkConstraint(argument, results)


class TestLocalAssignConstraint(TestConstraintBase):
	def setUp(self):
		self.db = MockDB()
		self.sys  = analysis.shape.RegionBasedShapeAnalysis(self.db)
	
		self.aLcl, self.aSlot, self.aExpr  = self.makeLocalObjs('a')
		self.bLcl, self.bSlot, self.bExpr  = self.makeLocalObjs('b')
		self.cLcl, self.cSlot, self.cExpr  = self.makeLocalObjs('c')
		self.xAttr = self.sys.canonical.fieldSlot(None, 'x')
		self.yAttr = self.sys.canonical.fieldSlot(None, 'y')

		self.axExpr = self.sys.canonical.fieldExpr(self.aExpr, self.xAttr)
		self.bxExpr = self.sys.canonical.fieldExpr(self.bExpr, self.xAttr)

		self.aRef = self.scalarIncrement(None, self.aSlot)
		self.bRef = self.scalarIncrement(None, self.bSlot)
		self.cRef = self.scalarIncrement(None, self.cSlot)
		self.abRef = self.scalarIncrement(self.aRef, self.bSlot)
		self.bcRef = self.scalarIncrement(self.bRef, self.cSlot)

		self.xRef = self.scalarIncrement(None, self.xAttr)

		self.inputPoint  = 0
		self.outputPoint = 1

		# b = a
		self.constraint = analysis.shape.constraints.AssignmentConstraint(self.sys, self.inputPoint, self.outputPoint, self.aExpr, self.bExpr)


	def testNoAlias(self):
		# c -> c

		argument = (self.cRef, None, None)
		results = [
			(self.cRef, None, None),
			]
		self.checkConstraint(argument, results)


	def testArgAlias(self):
		# a -> ab
		argument = (self.aRef, None, None)
		results = [
			(self.abRef, None, None),
			]
		self.checkConstraint(argument, results)

	def testTargetAlias(self):
		# b -> null
		argument = (self.bRef, None, None)
		results = [
			]
		self.checkConstraint(argument, results)

	def testBothAlias(self):
		# ab -> ab
		argument = (self.abRef, None, None)
		results = [
			(self.abRef, None, None),
			]
		self.checkConstraint(argument, results)

	def testPartialAlias(self):
		# bc -> c
		argument = (self.bcRef, None, None)
		results = [
			(self.cRef, None, None),
			]
		self.checkConstraint(argument, results)


	def testHeapPath1(self):
		# x(a.x|) -> x(a.x,b.x|)
		argument = (self.xRef, (self.axExpr,), None)
		results = [
			(self.xRef, (self.axExpr, self.bxExpr,), None),
			]
		self.checkConstraint(argument, results)

	def testHeapPath2(self):
		# x(b.x|) -> x(|)
		argument = (self.xRef, (self.bxExpr,), None)
		results = [
			(self.xRef, None, None),
			]
		self.checkConstraint(argument, results)

	def testHeapPath3(self):
		# x(|a.x) -> x(|a.x,b.x)
		argument = (self.xRef, None, (self.axExpr,))
		results = [
			(self.xRef, None, (self.axExpr, self.bxExpr,)),
			]
		self.checkConstraint(argument, results)

	def testHeapPath4(self):
		# x(|b.x) -> x(|)
		argument = (self.xRef, None, (self.bxExpr,))
		results = [
			(self.xRef, None, None),
			]
		self.checkConstraint(argument, results)

class TestLoadAssignConstraint(TestConstraintBase):
	def setUp(self):
		self.db = MockDB()
		self.sys  = analysis.shape.RegionBasedShapeAnalysis(self.db)
		
		self.aLcl, self.aSlot, self.aExpr  = self.makeLocalObjs('a')
		self.bLcl, self.bSlot, self.bExpr  = self.makeLocalObjs('b')
		self.xAttr = self.sys.canonical.fieldSlot(None, 'x')
		self.yAttr = self.sys.canonical.fieldSlot(None, 'y')

		self.axExpr = self.sys.canonical.fieldExpr(self.aExpr, self.xAttr)
		self.bxExpr = self.sys.canonical.fieldExpr(self.bExpr, self.xAttr)
		self.axxExpr = self.sys.canonical.fieldExpr(self.axExpr, self.xAttr)


		self.aRef = self.scalarIncrement(None, self.aSlot)
		self.bRef = self.scalarIncrement(None, self.bSlot)
		self.xRef = self.scalarIncrement(None, self.xAttr)
		self.yRef = self.scalarIncrement(None, self.yAttr)

		self.axRef = self.scalarIncrement(self.aRef, self.xAttr)
		self.bxRef = self.scalarIncrement(self.bRef, self.xAttr)
		self.abxRef = self.scalarIncrement(self.bxRef, self.aSlot)

		self.inputPoint = 0
		self.outputPoint = 1

		# b = a.x
		self.constraint = analysis.shape.constraints.AssignmentConstraint(self.sys, self.inputPoint, self.outputPoint, self.axExpr, self.bExpr)

	

	def testTargetAlias(self):
		# b -> nil
		argument = (self.bRef, None, None)
		results = []
		self.checkConstraint(argument, results)

	def testExprAlias(self):
		# a -> a
		argument = (self.aRef, None, None)
		results = [
			(self.aRef, None, None),
			]
		self.checkConstraint(argument, results)

	def testAttrMayAlias(self):
		# x(|) -> x(|a.x), bx(a.x|)
		argument = (self.xRef, None, None)
		results = [
			(self.xRef, None, (self.axExpr,)),
			(self.bxRef, (self.axExpr,), None),
			]
		self.checkConstraint(argument, results)

	def testAttrMustAlias(self):
		# x(a.x|) -> bx(a.x|)
		argument = (self.xRef, (self.axExpr,), None)
		results = [
			(self.bxRef, (self.axExpr,), None),
			]
		self.checkConstraint(argument, results)


	def testAttrMustNotAlias(self):
		# x(a.x.x|a.x) -> x(a.x.x, b.x|a.x)
		
		argument = (self.xRef, (self.axxExpr,), (self.axExpr,))
		results = [
			(self.xRef, (self.axxExpr, self.bxExpr), (self.axExpr,)),
			]
		self.checkConstraint(argument, results)

	def testAttrLocalAlias(self):
		# bx1 -> x1, bx1
		argument = (self.bxRef, None, None)
		results = [
			(self.xRef, None, (self.axExpr,)),
			(self.bxRef, (self.axExpr,), None),
			]
		self.checkConstraint(argument, results)


	def testAttrExprAlias(self):
		# ax1 -> ax1, abx1
		argument = (self.axRef, None, None)
		results = [
			(self.axRef, None, (self.axExpr,)),
			(self.abxRef, (self.axExpr,), None),
			]
		self.checkConstraint(argument, results)


class TestStoreAssignConstraint(TestConstraintBase):
	def setUp(self):
		self.db = MockDB()
		self.sys  = analysis.shape.RegionBasedShapeAnalysis(self.db)
		
		self.aLcl, self.aSlot, self.aExpr  = self.makeLocalObjs('a')
		self.bLcl, self.bSlot, self.bExpr  = self.makeLocalObjs('b')

		self.xAttr = self.sys.canonical.fieldSlot(None, 'x')
		self.yAttr = self.sys.canonical.fieldSlot(None, 'y')

		self.axExpr = self.sys.canonical.fieldExpr(self.aExpr, self.xAttr)

		self.bxExpr = self.sys.canonical.fieldExpr(self.bExpr, self.xAttr)
		self.bxxExpr = self.sys.canonical.fieldExpr(self.bxExpr, self.xAttr)


		self.aRef = self.scalarIncrement(None, self.aSlot)
		self.bRef = self.scalarIncrement(None, self.bSlot)
		self.xRef = self.scalarIncrement(None, self.xAttr)
		self.yRef = self.scalarIncrement(None, self.yAttr)

		self.axRef = self.scalarIncrement(self.aRef, self.xAttr)
		self.bxRef = self.scalarIncrement(self.bRef, self.xAttr)
		self.bxxRef = self.scalarIncrement(self.bxRef, self.xAttr)

		self.abxRef = self.scalarIncrement(self.bxRef, self.aSlot)


		self.inputPoint = 0
		self.outputPoint = 1

		# b.x = a
		self.constraint = analysis.shape.constraints.AssignmentConstraint(self.sys, self.inputPoint, self.outputPoint, self.aExpr, self.bxExpr)

	def testTargetAlias(self):
		# a -> ax(b.x|)
		argument = (self.aRef, None, None)
		results = [
			(self.axRef, (self.bxExpr,), None),
			]
		self.checkConstraint(argument, results)


	def testHeapAlias(self):
		# x -> x(|b.x)
		argument = (self.xRef, None, None)
		results = [
			(self.xRef, None, (self.bxExpr,)),
			]
		self.checkConstraint(argument, results)		


	def testHeapMustAliasChild(self):
		# x(a.x | b.x) -> x(a.x, b.x.x | b.x)
		argument = (self.xRef, (self.axExpr,), (self.bxExpr,))
		results = [
			(self.xRef, (self.axExpr,self.bxxExpr), (self.bxExpr,)),
			]
		self.checkConstraint(argument, results)	


	def testNoAffect(self):
		# ax(b.x, b.x.x|) -> ax(b.x, b.x.x|)
		argument = (self.axRef, (self.bxExpr,self.bxxExpr), None)
		results = [
			(self.axRef, (self.bxExpr,self.bxxExpr), None),
			]
		self.checkConstraint(argument, results)	

	def testHeapMustAlias(self):
		# x(b.x|) -> null
		argument = (self.xRef, (self.bxExpr,), None)
		results = [
			]
		self.checkConstraint(argument, results)	

	def testHeapLocalMustAlias(self):
		# bx(b.x|) -> b
		argument = (self.bxRef, (self.bxExpr,), None)
		results = [
			(self.bRef, None, None),
			]
		self.checkConstraint(argument, results)	

	def testHeap2LocalMustAlias(self):
		# bxx(b.x|) -> bx(|b.x)
		argument = (self.bxxRef, (self.bxExpr,), None)
		results = [
			(self.bxRef, None, (self.bxExpr,)),
			]
		self.checkConstraint(argument, results)	



import time

class TestSimpleCase(TestConstraintBase):
	def setUp(self):
		self.db = MockDB()
		self.sys  = analysis.shape.RegionBasedShapeAnalysis(self.db)
		
		# Splice example from paper


		x, self.xSlot, self.xExpr  = self.makeLocalObjs('x')
		y, self.ySlot, self.yExpr  = self.makeLocalObjs('y')
		z, self.zSlot, self.zExpr  = self.makeLocalObjs('z')
		t, self.tSlot, self.tExpr  = self.makeLocalObjs('t')
		q, self.qSlot, self.qExpr  = self.makeLocalObjs('q')


		self.xRef = self.scalarIncrement(None, self.xSlot)
		self.yRef = self.scalarIncrement(None, self.ySlot)
		self.nSlot = self.sys.canonical.fieldSlot(None, ('LowLevel', 'n'))

		self.nRef = self.scalarIncrement(None, self.nSlot)
		self.n2Ref = self.scalarIncrement(self.nRef, self.nSlot)


		# t = x
		# x = t.n
		# q = y.n
		# t.n = q
		# y.n = t
		# y = t.n

		# tn(y.n|)

		# tn(|t.n)
		# tny(t.n|)

		# HACK should really be doing a convertToBool?
		cond = ast.Condition(ast.Suite([]), x)
		
		body = ast.Suite([
			ast.Assign(x, t),
			ast.Assign(ast.Load(t, 'LowLevel', ast.Existing('n')), x),
			ast.Assign(ast.Load(y, 'LowLevel', ast.Existing('n')), q),
			ast.Store(t, 'LowLevel', ast.Existing('n'), q),
			ast.Delete(q),
			ast.Store(y, 'LowLevel', ast.Existing('n'), t),
			ast.Assign(ast.Load(t, 'LowLevel', ast.Existing('n')), y),
			])
		
		else_ = ast.Suite([])

		loop = ast.While(cond, body, else_)

		self.body = ast.Suite([
			ast.Assign(y, z),
			loop,
			ast.Return(z)
			])


		self.code = ast.Code(None, [x, y], ['x', 'y'], None, None, ast.Local('internal_return'), self.body)
		self.func = ast.Function('test', self.code)


		a, self.aSlot, self.aExpr  = self.makeLocalObjs('a')
		b, self.bSlot, self.bExpr  = self.makeLocalObjs('b')
		c, self.cSlot, self.cExpr  = self.makeLocalObjs('c')

		self.aRef = self.scalarIncrement(None, self.aSlot)
		self.bRef = self.scalarIncrement(None, self.bSlot)
		self.cRef = self.scalarIncrement(None, self.cSlot)

		dc = ast.DirectCall(self.func, None, [a,b], [], None, None)
		self.caller = ast.Suite([
			ast.Assign(dc, c),
			])

		invocation = (self.caller, dc, self.func)


		self.context = None
		self.cs = True

		# Make a dummy invocation
		self.db.addInvocation(None, self.context, dc, self.func, self.context)

		self.funcInput,  self.funcOutput   = self.makeConstraints(self.func)
		self.callerInput, self.callerOutput = self.makeConstraints(self.caller)


	def makeConstraints(self, func):
		builder = self.sys.constraintbuilder
		builder.process(func)
		return builder.statementPre[func], builder.statementPost[func]


	def createInput(self, ref):
		entry = ref if self.cs else None
		argument = (ref, None, None)
		conf, secondary = self.convert(argument, entry)
		self.setInput(conf, secondary)

	def setInput(self, conf, secondary):
		self.sys.environment.merge(self.sys, self.inputPoint, self.context, conf, secondary)

	def dumpPoint(self, givenPoint):
		mapping = self.sys.environment._secondary
		       
		for (point, context, conf), secondary in mapping.iteritems():
			if point != givenPoint: continue

			print conf.entrySet
			print conf.currentSet
			if secondary.hits:
				print "hits"
				for hit in secondary.hits:
					print '\t', hit
			if secondary.misses:
				print "misses"
				for miss in secondary.misses:
					print '\t', miss
			print

	def dumpStatistics(self):
		print "Entries:", len(self.sys.environment._secondary)
		print "Unique Config:", len(self.sys.canonical.configurationCache)
		print "Max Worklist:", self.sys.worklist.maxLength
		print "Steps:", "%d/%d" % (self.sys.worklist.usefulSteps, self.sys.worklist.steps)


	def process(self):
		start = time.clock()
		self.sys.process()
		end = time.clock()
		self.elapsed = end-start

	def dump(self, point):
		print
		print "/%s\\" % ("*"*80)
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

	def testLocal(self):
		self.inputPoint = self.funcInput
		self.outputPoint = self.funcOutput
		
		self.createInput(self.xRef)
		self.createInput(self.yRef)
		self.createInput(self.nRef)
		#self.createInput(self.n2Ref)

		self.process()

		self.dump(self.outputPoint)


	def testCall(self):
		self.inputPoint = self.callerInput
		self.outputPoint = self.callerOutput
		#self.outputPoint = self.funcOutput
		
		self.createInput(self.aRef)
		self.createInput(self.bRef)
		self.createInput(self.nRef)

		self.process()

		self.dump(self.outputPoint)
