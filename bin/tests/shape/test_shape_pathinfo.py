from __future__ import absolute_import

import unittest

import analysis.shape.model.canonical as canonical
import analysis.shape.model.pathinformation as pathinformation


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

		filtera = info.filterUnstable(None, self.a.slot, ())
		self.assertEqual(filtera.classifyHitMiss(self.an), (False, False))
		self.assertEqual(filtera.classifyHitMiss(self.bn), (True,  False))

		filterb = info.filterUnstable(None, self.b.slot, ())
		self.assertEqual(filterb.classifyHitMiss(self.an), (True,   False))
		self.assertEqual(filterb.classifyHitMiss(self.bn), (False,  False))


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

		self.assertEqual(info.classifyHitMiss(self.an), (True, False))
		self.assertEqual(info.classifyHitMiss(self.bn), (True, False))


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
