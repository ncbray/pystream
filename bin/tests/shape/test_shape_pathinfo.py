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

		filtera = info.filterUnstable(self.a.slot)
		self.assertEqual(filtera.classifyHitMiss(self.an), (False, False))
		self.assertEqual(filtera.classifyHitMiss(self.bn), (True,  False))

		filterb = info.filterUnstable(self.b.slot)
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



class TestPathInfoSplit(unittest.TestCase):
	def makeLocalExpr(self, lcl):
		lclSlot = self.canonical.localSlot(lcl)
		lclExpr = self.canonical.localExpr(lclSlot)
		return lclExpr

	def makeExpr(self, root, *fields):
		expr = root
		for slot in fields:
			expr = self.canonical.fieldExpr(expr, slot)
		return expr

	def setUp(self):
		self.canonical = canonical.CanonicalObjects()
		self.f = self.canonical.fieldSlot(None, 'f')
		self.l = self.canonical.fieldSlot(None, 'l')
		self.r = self.canonical.fieldSlot(None, 'r')

		self.x    = self.makeLocalExpr('x')
		self.y    = self.makeLocalExpr('y')
		self.z    = self.makeLocalExpr('z')
		self.this = self.makeLocalExpr('this')

		self.xf  = self.makeExpr(self.x, self.f)
		self.yr  = self.makeExpr(self.y, self.r)
		self.yrl = self.makeExpr(self.y, self.r, self.l)
		self.zf  = self.makeExpr(self.z, self.f)
		self.zfl  = self.makeExpr(self.z, self.f, self.l)

		self.tr = self.makeExpr(self.this, self.r)
		self.trl = self.makeExpr(self.this, self.r, self.l)
	
		self.paths = self.makeBase()


	def makeBase(self):
		paths = pathinformation.PathInformation()
		paths.union(self.xf, self.yrl)
		paths.union(self.yr, self.zf)
		paths.union(self.this, self.y)
		paths.inplaceUnionHitMiss((self.xf,), None)
		return paths
		
	def testHits(self):
		self.assertEqual(self.paths.classifyHitMiss(self.xf),  (True, False))
		self.assertEqual(self.paths.classifyHitMiss(self.yrl), (True, False))
		self.assertEqual(self.paths.classifyHitMiss(self.trl), (True, False))

		self.assertEqual(self.paths.classifyHitMiss(self.yr), (False, False))
		self.assertEqual(self.paths.classifyHitMiss(self.zf), (False, False))

		
