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

import analysis.shape.model.canonical as canonical
import analysis.shape.model.pathinformation as pathinformation

from util.tvl import *

class TestPathInformationBase(unittest.TestCase):
	def makeExprs(self, lcl):
		lclSlot = self.canonical.localSlot(lcl)
		lclExpr = self.canonical.localExpr(lclSlot)
		lclN = self.canonical.fieldExpr(lclExpr, self.nSlot)
		lclNN = self.canonical.fieldExpr(lclN, self.nSlot)
		return lclExpr, lclN, lclNN

	def setUp(self):
		self.canonical = canonical.CanonicalObjects()
		self.nSlot = self.canonical.fieldSlot(None, 'n')

		self.a, self.an, self.ann = self.makeExprs('a')
		self.b, self.bn, self.bnn = self.makeExprs('b')
		self.c, self.cn, self.cnn = self.makeExprs('c')
		self.d, self.dn, self.dnn = self.makeExprs('d')

		self.x, self.xn, self.xnn = self.makeExprs('x')
		self.y, self.yn, self.ynn = self.makeExprs('y')
		self.z, self.zn, self.znn = self.makeExprs('z')
		self.w, self.wn, self.wnn = self.makeExprs('w')


class TestPathInformation(TestPathInformationBase):
	def testHits1(self):
		# Makes sure that if the canonical hit is eliminated,
		# another one takes its place.
		info = pathinformation.PathInformation()
		info = info.unionHitMiss((self.an,self.bn), ())

		filtera = info.filterUnstable(self.a.slot)
		self.assertEqual(filtera.hit(self.an), TVLMaybe)
		self.assertEqual(filtera.hit(self.bn), TVLTrue)

		filterb = info.filterUnstable(self.b.slot)
		self.assertEqual(filterb.hit(self.an), TVLTrue)
		self.assertEqual(filterb.hit(self.bn), TVLMaybe)


	def testHits2(self):
		# Makes sure that if the canonical hit is eliminated,
		# another one takes its place.

		info = pathinformation.PathInformation()
		info.union(self.a, self.b)
		self.assert_(info.mustAlias(self.a, self.b))
		self.assert_(info.mustAlias(self.an, self.bn))

		info = info.unionHitMiss((self.an,), ())
		self.assert_(info.mustAlias(self.a, self.b))
		self.assert_(info.mustAlias(self.an, self.bn))

		self.assertEqual(info.hit(self.an), TVLTrue)
		self.assertEqual(info.hit(self.bn), TVLTrue)


	def testLoop(self):
		info = pathinformation.PathInformation()
		info.union(self.a, self.an)
		self.assert_(not info.mustAlias(self.a, self.b))
		self.assert_(not info.mustAlias(self.an, self.bn))

		self.assert_(info.mustAlias(self.a, self.an))
		self.assert_(info.mustAlias(self.an, self.ann))


	def testTricky1(self):
		info = pathinformation.PathInformation()
		info.union(self.an, self.bn)
		info.union(self.cn, self.dn)
		info.union(self.b, self.c)

		self.assert_(not info.mustAlias(self.a, self.b))
		self.assert_(info.mustAlias(self.b, self.c))
		self.assert_(not info.mustAlias(self.c, self.d))

		self.assert_(info.mustAlias(self.an, self.bn))
		self.assert_(info.mustAlias(self.an, self.cn))
		self.assert_(info.mustAlias(self.an, self.dn))
		self.assert_(info.mustAlias(self.bn, self.cn))
		self.assert_(info.mustAlias(self.bn, self.dn))
		self.assert_(info.mustAlias(self.cn, self.dn))


	def testTricky2(self):
		info = pathinformation.PathInformation()
		info.union(self.an, self.ann)
		info.union(self.dn, self.dnn)

		info.union(self.an, self.bn)
		info.union(self.cn, self.dn)
		info.union(self.b, self.c)

		self.assert_(not info.mustAlias(self.a, self.b))
		self.assert_(info.mustAlias(self.b, self.c))
		self.assert_(not info.mustAlias(self.c, self.d))

		self.assert_(info.mustAlias(self.an, self.bn))
		self.assert_(info.mustAlias(self.an, self.cn))
		self.assert_(info.mustAlias(self.an, self.dn))
		self.assert_(info.mustAlias(self.bn, self.cn))
		self.assert_(info.mustAlias(self.bn, self.dn))
		self.assert_(info.mustAlias(self.cn, self.dn))

		self.assert_(info.mustAlias(self.an, self.ann))
		self.assert_(info.mustAlias(self.bn, self.bnn))
		self.assert_(info.mustAlias(self.cn, self.cnn))
		self.assert_(info.mustAlias(self.dn, self.dnn))

		self.assert_(info.mustAlias(self.an, self.bnn))


	def testIntersect1(self):
		info1 = pathinformation.PathInformation()
		info1.union(self.a, self.an)
		self.assert_(info1.mustAlias(self.a, self.an))
		self.assert_(info1.mustAlias(self.a, self.ann))


		info2 = pathinformation.PathInformation()
		info2.union(self.a, self.ann)
		self.assert_(not info2.mustAlias(self.a, self.an))
		self.assert_(info2.mustAlias(self.a, self.ann))


		info3, changed = info1.inplaceMerge(info2)

		self.assert_(changed)
		self.assert_(not info3.mustAlias(self.a, self.an))
		self.assert_(info3.mustAlias(self.a, self.ann))

		info3, changed = info3.inplaceMerge(info1)
		self.assert_(not changed)
		self.assert_(not info3.mustAlias(self.a, self.an))
		self.assert_(info3.mustAlias(self.a, self.ann))

		info3, changed = info3.inplaceMerge(info2)
		self.assert_(not changed)
		self.assert_(not info3.mustAlias(self.a, self.an))
		self.assert_(info3.mustAlias(self.a, self.ann))


class PathInfoBase(unittest.TestCase):
	def makeLocalExpr(self, lcl):
		lclSlot = self.canonical.localSlot(lcl)
		lclExpr = self.canonical.localExpr(lclSlot)
		return lclExpr

	def makeExpr(self, root, *fields):
		expr = root
		for slot in fields:
			expr = self.canonical.fieldExpr(expr, slot)
		return expr

class TestPathInfoSplit(PathInfoBase):
	def setUp(self):
		self.canonical = canonical.CanonicalObjects()
		self.f = self.canonical.fieldSlot(None, 'f')
		self.l = self.canonical.fieldSlot(None, 'l')
		self.r = self.canonical.fieldSlot(None, 'r')

		self.x    = self.makeLocalExpr('x')
		self.y    = self.makeLocalExpr('y')
		self.z    = self.makeLocalExpr('z')
		self.t = self.makeLocalExpr('this')

		self.xf  = self.makeExpr(self.x, self.f)
		self.yr  = self.makeExpr(self.y, self.r)
		self.yrl = self.makeExpr(self.y, self.r, self.l)
		self.zf  = self.makeExpr(self.z, self.f)
		self.zfl  = self.makeExpr(self.z, self.f, self.l)

		self.tr = self.makeExpr(self.t, self.r)
		self.trl = self.makeExpr(self.t, self.r, self.l)

		self.et = self.canonical.extendedParameter(self.t)
		self.etr = self.canonical.extendedParameter(self.tr)
		self.etrl = self.canonical.extendedParameter(self.trl)

		self.paths = self.makeBase()


	def makeBase(self):
		paths = pathinformation.PathInformation()
		paths.union(self.xf, self.yrl)
		paths.union(self.yr, self.zf)
		paths.union(self.t, self.y)
		paths.inplaceUnionHitMiss((self.xf,), None)
		return paths

	def extendBase(self):
		parameterSlots = set((self.t.slot,))
		self.extendedParams = self.paths.extendParameters(self.canonical, parameterSlots)

	def testHits(self):
		self.assertEqual(self.paths.hit(self.xf),  TVLTrue)
		self.assertEqual(self.paths.hit(self.yrl), TVLTrue)
		self.assertEqual(self.paths.hit(self.trl), TVLTrue)

		self.assertEqual(self.paths.hit(self.yr), TVLMaybe)
		self.assertEqual(self.paths.hit(self.zf), TVLMaybe)

	def testExtendParameters(self):
		self.extendBase()

		self.assertEqual(self.paths.hit(self.etrl),  TVLTrue)

		self.assert_(self.paths.mustAlias(self.etr, self.tr))
		self.assert_(self.paths.mustAlias(self.etr, self.yr))
		self.assert_(self.paths.mustAlias(self.etr, self.zf))

	def testSplit(self):
		self.extendBase()

		accessed = set([self.l, self.r, self.t.slot])
		def accessedCallback(slot):
			return slot in accessed

		self.assert_(self.paths.mustAlias(self.yr, self.zf))

		accessed, hidden = self.paths.split(self.extendedParams, accessedCallback)

		self.assert_(accessed.mustAlias(self.tr, self.etr))
		self.assert_(accessed.mustAlias(self.trl, self.etrl))
		self.assert_(not accessed.mustAlias(self.y, self.et))

		self.assert_(not accessed.mustAlias(self.yr, self.zf))


		self.assert_(hidden.mustAlias(self.zf, self.etr))
		self.assert_(hidden.mustAlias(self.xf, self.etrl))
		self.assert_(hidden.mustAlias(self.y, self.et))

		self.assert_(not hidden.mustAlias(self.yr, self.zf))

class TestUglyPathInfoSplit(PathInfoBase):
	def setUp(self):
		self.canonical = canonical.CanonicalObjects()
		self.l = self.canonical.fieldSlot(None, 'l')
		self.r = self.canonical.fieldSlot(None, 'r')

		self.x    = self.makeLocalExpr('x')
		self.y    = self.makeLocalExpr('y')

		self.xl  = self.makeExpr(self.x, self.l)
		self.xlr  = self.makeExpr(self.x, self.l, self.r)
		self.xlrr  = self.makeExpr(self.x, self.l, self.r, self.r)

		self.yr  = self.makeExpr(self.y, self.r)
		self.yrr  = self.makeExpr(self.y, self.r, self.r)
		self.yrrr  = self.makeExpr(self.y, self.r, self.r, self.r)


		self.paths = self.makeBase()


	def makeBase(self):
		paths = pathinformation.PathInformation()
		paths.union(self.xl, self.yr)
		paths.inplaceUnionHitMiss((self.xlrr,), None)
		return paths

	def extendBase(self):
		parameterSlots = set()
		self.extendedParams = self.paths.extendParameters(self.canonical, parameterSlots)

	def testHits(self):
		self.assertEqual(self.paths.hit(self.xlrr),  TVLTrue)
		self.assertEqual(self.paths.hit(self.yrrr), TVLTrue)

		self.assertEqual(self.paths.hit(self.xlr), TVLMaybe)
		self.assertEqual(self.paths.hit(self.yrr), TVLMaybe)

		self.assertEqual(self.paths.hit(self.xl), TVLMaybe)
		self.assertEqual(self.paths.hit(self.yr), TVLMaybe)

		self.assertEqual(self.paths.hit(self.x), TVLMaybe)
		self.assertEqual(self.paths.hit(self.y), TVLMaybe)

		self.assert_(self.paths.mustAlias(self.xlr, self.yrr))

	def testSplit(self):
		self.extendBase() # Should do nothing?

		accessed = set([self.l])
		def accessedCallback(slot):
			return slot in accessed

		accessed, hidden = self.paths.split(self.extendedParams, accessedCallback)


		self.assertEqual(accessed.hit(self.xlrr),  TVLTrue)
		self.assertEqual(accessed.hit(self.yrrr), TVLMaybe)
		self.assert_(not accessed.mustAlias(self.xlr, self.yrr))

		self.assertEqual(hidden.hit(self.xlrr),  TVLMaybe)
		self.assertEqual(hidden.hit(self.yrrr), TVLTrue)
		self.assert_(not hidden.mustAlias(self.xlr, self.yrr))

##		accessed.dump()
##		print "="*80
##		hidden.dump()
