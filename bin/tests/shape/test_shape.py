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

from tests.shape.shape_base import *

import analysis.shape.transferfunctions

from util.tvl import *

class TestExpressions(TestConstraintBase):
	def shapeSetUp(self):
		self.fielda = self.sys.canonical.fieldSlot(None, 'a')
		self.fieldb = self.sys.canonical.fieldSlot(None, 'b')

		self.localz = self.sys.canonical.localSlot('zero')
		self.localo = self.sys.canonical.localSlot('one')

		self.zero     = self.sys.canonical.localExpr(self.localz)
		self.zero_a   = self.expr(self.zero, self.fielda)
		self.zero_a_a = self.expr(self.zero, self.fielda, self.fielda)
		self.zero_a_b = self.expr(self.zero, self.fielda, self.fieldb)

		self.zero_b   = self.expr(self.zero, self.fieldb)
		self.zero_b_a = self.expr(self.zero, self.fieldb, self.fielda)
		self.zero_b_b = self.expr(self.zero, self.fieldb, self.fieldb)

		self.one     = self.sys.canonical.localExpr(self.localo)
		self.one_a   = self.expr(self.one, self.fielda)
		self.one_a_a = self.expr(self.one, self.fielda, self.fielda)
		self.one_a_b = self.expr(self.one, self.fielda, self.fieldb)

		self.one_b   = self.expr(self.one, self.fieldb)
		self.one_b_a = self.expr(self.one, self.fieldb, self.fielda)
		self.one_b_b = self.expr(self.one, self.fieldb, self.fieldb)

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


	def testUpdateHitMiss1(self):
		# zero = zero.a
		e0, e1 =  self.zero, self.zero_a

		# How do we know self.zero_a != self.zero_a_b?

		slot = e0.slot
		b0 = False
		b1 = False

		hits   = set((self.zero_a_b,))
		misses = set((self.one_a_b, self.zero_a_a))
		paths = self.sys.canonical.paths(hits, misses)

		newPaths = analysis.shape.transferfunctions.updateHitMiss(self.sys, e0, e1, b0, b1, slot, paths)

		# The retargeted hit
		# HACK
		#expectedHits   = set((self.zero_b,))
		expectedHits   = None

		# This original miss is not disrupted, and as the configuration does not alias to e1, it must now miss e0
		# HACK precision lost if RHS and LHS conflict
		# TODO improve precision
		#expectedMisses = set((self.one_a_b, self.zero_a))
		expectedMisses = set((self.one_a_b,))

		self.checkHitMiss(newPaths, expectedHits, expectedMisses)



	def testUpdateHitMiss2(self):
		# zero = zero.a
		e0 =  self.zero
		e1 =  self.zero_a
		slot = e0.slot
		hits   = set((self.zero_a_b,))
		misses = set((self.one_a_b,))
		b0 = False
		b1 = True

		paths = self.sys.canonical.paths(hits, misses)
		newPaths = analysis.shape.transferfunctions.updateHitMiss(self.sys, e0, e1, b0, b1, slot, paths)

		# HACK precision lost if RHS and LHS conflict
		#expectedHits = set((self.zero_b,))
		# TODO improve precision
		expectedHits = None
		expectedMisses = set((self.one_a_b,))

		self.checkHitMiss(newPaths, expectedHits, expectedMisses)


	def testUpdateHitMiss3(self):
		# zero = zero.a
		e0 =  self.zero
		e1 =  self.zero_a
		slot = e0.slot
		hits   = set((self.zero_a_b,))
		misses = set((self.one_a_b,))
		b0 = True
		b1 = False

		paths = self.sys.canonical.paths(hits, misses)
		newPaths = analysis.shape.transferfunctions.updateHitMiss(self.sys, e0, e1, b0, b1, slot, paths)

		# HACK precision lost if RHS and LHS conflict
		#expectedHits = set((self.zero, self.zero_b))
		# TODO improve precision
		expectedHits = None
		expectedMisses = set((self.one_a_b,))

		self.checkHitMiss(newPaths, expectedHits, expectedMisses)

	def checkHitMiss(self, newPaths, hits, misses):
		if hits:
			for hit in hits:
				self.assertEqual(newPaths.hit(hit), TVLTrue)

		if misses:
			for miss in misses:
				self.assertEqual(newPaths.hit(miss), TVLFalse)



class TestReferenceCounts(TestConstraintBase):
	def shapeSetUp(self):
		self.fielda = self.sys.canonical.fieldSlot(None, 'a')
		self.fieldb = self.sys.canonical.fieldSlot(None, 'b')

		self.localz = self.sys.canonical.localSlot('zero')
		self.localo = self.sys.canonical.localSlot('one')

		self.null = self.sys.canonical.rcm.getCanonical({}, frozenset())

	def scalarIncrement(self, rc, slot):
		next = self.sys.canonical.incrementRef(rc, slot)
		self.assertEqual(len(next), 1)
		return next[0]

	def testIncrementSaturate(self):
		current = None
		slot = self.fielda

		# HACK to get the refcount k
		for i in range(self.sys.canonical.rcm.k+1):
			next = self.scalarIncrement(current, slot)

			self.assertNotEqual(current, next)

			self.assertEqual(len(next.counts), 1)
			for cslot, count in next.counts.iteritems():
				self.assertEqual(cslot, slot)
				self.assertEqual(count, i+1)

			current = next

		next = self.scalarIncrement(current, slot)
		self.assertEqual(current, next)

	def testDecrement(self):
		slot = self.fielda

		inc1 = self.refs(slot)
		inc2 = self.scalarIncrement(inc1, slot)
		inc3 = self.scalarIncrement(inc2, slot)

		# Decrementing infinity can yield two different configurations
		dec2 = self.sys.canonical.decrementRef(inc3, slot)
		self.assertEqual(set(dec2), set((inc2,inc3)))

		# Decrementing an "intermediate" value will result in a single
		dec1 = self.sys.canonical.decrementRef(inc2, slot)
		self.assertEqual(dec1, (inc1,))

		# Decrementing one can eliminate the reference count
		# A "null" object is still returned, however.
		dec0 = self.sys.canonical.decrementRef(inc1, slot)
		self.assertEqual(dec0, (self.null,))



class TestCopyConstraint(TestConstraintBase):
	def shapeSetUp(self):
		self.cLcl, self.cSlot, self.cExpr  = self.makeLocalObjs('c')
		self.cRef = self.refs(self.cSlot)

		# b = a
		self.setConstraint(analysis.shape.constraints.CopyConstraint(self.sys, self.inputPoint, self.outputPoint))

	def testNoAlias(self):
		# c -> c

		argument = (self.cRef, None, None)
		results = [
			(self.cRef, None, None),
			]
		self.checkTransfer(argument, results)


class TestLocalAssignConstraint(TestConstraintBase):
	def shapeSetUp(self):
		self.aLcl, self.aSlot, self.aExpr  = self.makeLocalObjs('a')
		self.bLcl, self.bSlot, self.bExpr  = self.makeLocalObjs('b')
		self.cLcl, self.cSlot, self.cExpr  = self.makeLocalObjs('c')
		self.xAttr = self.sys.canonical.fieldSlot(None, 'x')
		self.yAttr = self.sys.canonical.fieldSlot(None, 'y')

		self.axExpr = self.expr(self.aExpr, self.xAttr)
		self.bxExpr = self.expr(self.bExpr, self.xAttr)

		self.aRef  = self.refs(self.aSlot)
		self.bRef  = self.refs(self.bSlot)
		self.cRef  = self.refs(self.cSlot)
		self.abRef = self.refs(self.aSlot, self.bSlot)
		self.bcRef = self.refs(self.bSlot, self.cSlot)

		self.xRef = self.refs(self.xAttr)

		# b = a
		self.setConstraint(analysis.shape.constraints.AssignmentConstraint(self.sys, self.inputPoint, self.outputPoint, self.aExpr, self.bExpr))


	def testNoAlias(self):
		# c -> c

		argument = (self.cRef, None, None)
		results = [
			(self.cRef, None, None),
			]
		self.checkTransfer(argument, results)


	def testArgAlias(self):
		# a -> ab
		argument = (self.aRef, None, None)
		results = [
			(self.abRef, None, None),
			]
		self.checkTransfer(argument, results)

	def testTargetAlias(self):
		# b -> null
		argument = (self.bRef, None, None)
		results = [
			]
		self.checkTransfer(argument, results)

	def testBothAlias(self):
		# ab -> ab
		argument = (self.abRef, None, None)
		results = [
			(self.abRef, None, None),
			]
		self.checkTransfer(argument, results)

	def testPartialAlias(self):
		# bc -> c
		argument = (self.bcRef, None, None)
		results = [
			(self.cRef, None, None),
			]
		self.checkTransfer(argument, results)


	def testHeapPath1(self):
		# x(a.x|) -> x(a.x,b.x|)
		argument = (self.xRef, (self.axExpr,), None)
		results = [
			(self.xRef, (self.axExpr, self.bxExpr,), None),
			]
		self.checkTransfer(argument, results)

	def testHeapPath2(self):
		# x(b.x|) -> x(|)
		argument = (self.xRef, (self.bxExpr,), None)
		results = [
			(self.xRef, None, None, (self.bxExpr,)),
			]
		self.checkTransfer(argument, results)

	def testHeapPath3(self):
		# x(|a.x) -> x(|a.x,b.x)
		argument = (self.xRef, None, (self.axExpr,))
		results = [
			(self.xRef, None, (self.axExpr, self.bxExpr,)),
			]
		self.checkTransfer(argument, results)

	def testHeapPath4(self):
		# x(|b.x) -> x(|)
		argument = (self.xRef, None, (self.bxExpr,))
		results = [
			(self.xRef, None, None, (self.bxExpr,)),
			]
		self.checkTransfer(argument, results)

class TestLoadAssignConstraint(TestConstraintBase):
	def shapeSetUp(self):
		self.aLcl, self.aSlot, self.aExpr  = self.makeLocalObjs('a')
		self.bLcl, self.bSlot, self.bExpr  = self.makeLocalObjs('b')
		self.xAttr = self.sys.canonical.fieldSlot(None, 'x')
		self.yAttr = self.sys.canonical.fieldSlot(None, 'y')

		self.axExpr  = self.expr(self.aExpr, self.xAttr)
		self.axxExpr = self.expr(self.aExpr, self.xAttr, self.xAttr)

		self.bxExpr  = self.expr(self.bExpr, self.xAttr)


		self.aRef = self.refs(self.aSlot)
		self.bRef = self.refs(self.bSlot)
		self.xRef = self.refs(self.xAttr)
		self.yRef = self.refs(self.yAttr)

		self.axRef  = self.refs(self.aSlot, self.xAttr)
		self.bxRef  = self.refs(self.bSlot, self.xAttr)
		self.abxRef = self.refs(self.aSlot, self.bSlot, self.xAttr)

		# b = a.x
		self.setConstraint(analysis.shape.constraints.AssignmentConstraint(self.sys, self.inputPoint, self.outputPoint, self.axExpr, self.bExpr))



	def testTargetAlias(self):
		# b -> nil
		argument = (self.bRef, None, None)
		results = []
		self.checkTransfer(argument, results)

	def testExprAlias(self):
		# a -> a
		argument = (self.aRef, None, None)
		results = [
			(self.aRef, None, None),
			]
		self.checkTransfer(argument, results)

	def testAttrMayAlias(self):
		# x(|) -> x(|a.x), bx(a.x|)
		argument = (self.xRef, None, None)
		results = [
			(self.xRef, None, (self.axExpr,)),
			(self.bxRef, (self.axExpr,), None),
			]
		self.checkTransfer(argument, results)

	def testAttrMustAlias(self):
		# x(a.x|) -> bx(a.x|)
		argument = (self.xRef, (self.axExpr,), None)
		results = [
			(self.bxRef, (self.axExpr,), None),
			]
		self.checkTransfer(argument, results)


	def testAttrMustNotAlias(self):
		# x(a.x.x|a.x) -> x(a.x.x, b.x|a.x)

		argument = (self.xRef, (self.axxExpr,), (self.axExpr,))
		results = [
			(self.xRef, (self.axxExpr, self.bxExpr), (self.axExpr,)),
			]
		self.checkTransfer(argument, results)

	def testAttrLocalAlias(self):
		# bx1 -> x1, bx1
		argument = (self.bxRef, None, None)
		results = [
			(self.xRef, None, (self.axExpr,)),
			(self.bxRef, (self.axExpr,), None),
			]
		self.checkTransfer(argument, results)


	def testAttrExprAlias(self):
		# ax1 -> ax1, abx1
		argument = (self.axRef, None, None)
		results = [
			(self.axRef, None, (self.axExpr,)),
			(self.abxRef, (self.axExpr,), None),
			]
		self.checkTransfer(argument, results)


class TestStoreAssignConstraint(TestConstraintBase):
	def shapeSetUp(self):
		self.aLcl, self.aSlot, self.aExpr  = self.makeLocalObjs('a')
		self.bLcl, self.bSlot, self.bExpr  = self.makeLocalObjs('b')

		self.xAttr = self.sys.canonical.fieldSlot(None, 'x')
		self.yAttr = self.sys.canonical.fieldSlot(None, 'y')

		self.axExpr  = self.expr(self.aExpr, self.xAttr)

		self.bxExpr  = self.expr(self.bExpr, self.xAttr)
		self.bxxExpr = self.expr(self.bExpr, self.xAttr, self.xAttr)

		self.aRef = self.refs(self.aSlot)
		self.bRef = self.refs(self.bSlot)
		self.xRef = self.refs(self.xAttr)
		self.yRef = self.refs(self.yAttr)

		self.axRef  = self.refs(self.aSlot, self.xAttr)
		self.bxRef  = self.refs(self.bSlot, self.xAttr)
		self.bxxRef = self.refs(self.bSlot, self.xAttr, self.xAttr)

		self.abxRef = self.refs(self.aSlot, self.bSlot, self.xAttr)

		# b.x = a
		self.setConstraint(analysis.shape.constraints.AssignmentConstraint(self.sys, self.inputPoint, self.outputPoint, self.aExpr, self.bxExpr))

	def testTargetAlias(self):
		# a -> ax(b.x|)
		argument = (self.aRef, None, None)
		results = [
			(self.axRef, (self.bxExpr,), None),
			]
		self.checkTransfer(argument, results)


	def testHeapAlias(self):
		# x -> x(|b.x)
		argument = (self.xRef, None, None)
		results = [
			(self.xRef, None, (self.bxExpr,)),
			]
		self.checkTransfer(argument, results)


	def testHeapMustAliasChild(self):
		# x(a.x | b.x) -> x(a.x, b.x.x | b.x)
		argument = (self.xRef, (self.axExpr,), (self.bxExpr,))
		results = [
			# TODO depends on if "stable" paths are preserved
			#(self.xRef, (self.axExpr,self.bxxExpr), (self.bxExpr,)),
			(self.xRef, (), (self.bxExpr,)),
			]
		self.checkTransfer(argument, results)


	def testNoAffect(self):
		# ax(b.x, b.x.x|) -> ax(b.x, b.x.x|)
		argument = (self.axRef, (self.bxExpr,self.bxxExpr), None)
		results = [
			(self.axRef, (self.bxExpr,self.bxxExpr), None),
			]
		self.checkTransfer(argument, results)

	def testHeapMustAlias(self):
		# x(b.x|) -> null
		argument = (self.xRef, (self.bxExpr,), None)
		results = [
			]
		self.checkTransfer(argument, results)

	def testHeapLocalMustAlias(self):
		# bx(b.x|) -> b
		argument = (self.bxRef, (self.bxExpr,), None)
		results = [
			#(self.bRef, None, None, (self.bxExpr,)),
			# HACK bxExpr should not be a miss, as it is trivially computable...
			(self.bRef, None, None),
			]
		self.checkTransfer(argument, results)

	def testHeap2LocalMustAlias(self):
		# bxx(b.x|) -> bx(|b.x)
		argument = (self.bxxRef, (self.bxExpr,), None)
		results = [
			(self.bxRef, None, (self.bxExpr,)),
			]
		self.checkTransfer(argument, results)
