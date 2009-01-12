from __future__ import absolute_import

import unittest

import analysis.shape.path as path
import analysis.shape.model.canonical as canonical


class TestUnionFind(unittest.TestCase):

	def testUnion(self):
		u = path.UnionFind()

		u.union(1, 2, 3)
		u.union(4, 5, 6)

		# Set 1
		self.assertEquals(u[1], u[2])
		self.assertEquals(u[1], u[3])

		# Set 2
		self.assertEquals(u[4], u[5])
		self.assertEquals(u[4], u[6])

		# Set != Set
		self.assertNotEquals(u[1], u[4])

		# Set != untracked
		self.assertNotEquals(u[1], u[7])

		# Make sure we're clean.
		self.assertEquals(len(u.parents), 6)
		self.assertEquals(len(u.weights), 2)


class TestEquivilenceBase(unittest.TestCase):
	def makeExprs(self, lcl):
		lclSlot = self.canonical.localSlot(lcl)
		lclExpr = self.canonical.localExpr(lclSlot)
		lclN = self.canonical.fieldExpr(lclExpr, self.nSlot)
		lclNN = self.canonical.fieldExpr(lclN, self.nSlot)
		return lclExpr, lclN, lclNN

	def setUp(self):
		self.canonical = canonical.CanonicalObjects()
		self.pe = path.PathEquivalence(self.canonical.fieldExpr)
		self.nSlot = self.canonical.fieldSlot(None, 'n')

		self.a, self.an, self.ann = self.makeExprs('a')
		self.b, self.bn, self.bnn = self.makeExprs('b')
		self.c, self.cn, self.cnn = self.makeExprs('c')

		self.x, self.xn, self.xnn = self.makeExprs('x')
		self.y, self.yn, self.ynn = self.makeExprs('y')
		self.z, self.zn, self.znn = self.makeExprs('z')
		self.w, self.wn, self.wnn = self.makeExprs('w')	

	def dump(self):
		print
		print "DUMP"
		self.pe.dump()
		print


class TestPathEquivalence(TestEquivilenceBase):
	def testUnion1(self):
		self.pe.union(self.x, self.y)
		self.assertEqual(self.pe.canonical(self.x),   self.pe.canonical(self.y))
		self.assertEqual(self.pe.canonical(self.xn),  self.pe.canonical(self.yn))
		self.assertEqual(self.pe.canonical(self.xnn), self.pe.canonical(self.ynn))


	def testUnion2(self):
		self.pe.union(self.xn, self.yn)
		self.assertNotEqual(self.pe.canonical(self.x),   self.pe.canonical(self.y))
		self.assertEqual(self.pe.canonical(self.xn),     self.pe.canonical(self.yn))
		self.assertEqual(self.pe.canonical(self.xnn),    self.pe.canonical(self.ynn))

	def testUnion3(self):
		self.pe.union(self.xnn, self.ynn)
		self.assertNotEqual(self.pe.canonical(self.x),   self.pe.canonical(self.y))
		self.assertNotEqual(self.pe.canonical(self.xn),  self.pe.canonical(self.yn))
		self.assertEqual(self.pe.canonical(self.xnn),    self.pe.canonical(self.ynn))

	def testRecursive(self):
		self.pe.union(self.x, self.xn)
		self.assertEqual(self.pe.canonical(self.x),   self.pe.canonical(self.xn))
		self.assertEqual(self.pe.canonical(self.x),   self.pe.canonical(self.xnn))


	def testTricky1_0(self):
		self.pe.union(self.xn, self.yn)
		self.pe.union(self.x, self.z)

		self.assertEqual(self.pe.canonical(self.xn),   self.pe.canonical(self.yn))
		self.assertEqual(self.pe.canonical(self.zn),   self.pe.canonical(self.xn))
		self.assertEqual(self.pe.canonical(self.zn),   self.pe.canonical(self.yn))

		self.assertEqual(self.pe.canonical(self.znn),   self.pe.canonical(self.ynn))

	def testTricky1_1(self):
		self.pe.union(self.xn, self.yn)
		self.pe.union(self.z, self.x)


		self.assertEqual(self.pe.canonical(self.xn),   self.pe.canonical(self.yn))
		self.assertEqual(self.pe.canonical(self.zn),   self.pe.canonical(self.xn))
		self.assertEqual(self.pe.canonical(self.zn),   self.pe.canonical(self.yn))

		self.assertEqual(self.pe.canonical(self.znn),   self.pe.canonical(self.ynn))

	def testTricky1_2(self):
		self.pe.union(self.yn, self.xn)
		self.pe.union(self.x, self.z)

		self.assertEqual(self.pe.canonical(self.xn),   self.pe.canonical(self.yn))
		self.assertEqual(self.pe.canonical(self.zn),   self.pe.canonical(self.xn))
		self.assertEqual(self.pe.canonical(self.zn),   self.pe.canonical(self.yn))

		self.assertEqual(self.pe.canonical(self.znn),   self.pe.canonical(self.ynn))

	def testTricky1_3(self):
		self.pe.union(self.yn, self.xn)
		self.pe.union(self.z, self.x)

		self.assertEqual(self.pe.canonical(self.xn),   self.pe.canonical(self.yn))
		self.assertEqual(self.pe.canonical(self.zn),   self.pe.canonical(self.xn))
		self.assertEqual(self.pe.canonical(self.zn),   self.pe.canonical(self.yn))

		self.assertEqual(self.pe.canonical(self.znn),   self.pe.canonical(self.ynn))


	def testTricky2(self):
		self.pe.union(self.xnn, self.ynn)
		self.pe.union(self.z, self.x)

		self.assertNotEqual(self.pe.canonical(self.xn),   self.pe.canonical(self.yn))
		self.assertEqual(self.pe.canonical(self.zn),   self.pe.canonical(self.xn))
		self.assertNotEqual(self.pe.canonical(self.zn),   self.pe.canonical(self.yn))

		self.assertEqual(self.pe.canonical(self.xnn),   self.pe.canonical(self.ynn))
		self.assertEqual(self.pe.canonical(self.znn),   self.pe.canonical(self.xnn))
		self.assertEqual(self.pe.canonical(self.znn),   self.pe.canonical(self.ynn))


	def testTricky3_0(self):
		self.pe.union(self.xn, self.yn)
		self.pe.union(self.wn, self.zn)
		self.pe.union(self.z, self.x)

		self.assertEqual(self.pe.canonical(self.xn),   self.pe.canonical(self.yn))
		self.assertEqual(self.pe.canonical(self.zn),   self.pe.canonical(self.wn))

		self.assertEqual(self.pe.canonical(self.xn),   self.pe.canonical(self.zn))

		self.assertNotEqual(self.pe.canonical(self.x),   self.pe.canonical(self.y))
		self.assertNotEqual(self.pe.canonical(self.z),   self.pe.canonical(self.w))
		self.assertEqual(self.pe.canonical(self.x),   self.pe.canonical(self.z))


	def testTricky3_1(self):
		self.pe.union(self.yn, self.xn)
		self.pe.union(self.wn, self.zn)
		self.pe.union(self.z, self.x)

		self.assertEqual(self.pe.canonical(self.xn),   self.pe.canonical(self.yn))
		self.assertEqual(self.pe.canonical(self.zn),   self.pe.canonical(self.wn))

		self.assertEqual(self.pe.canonical(self.xn),   self.pe.canonical(self.zn))

		self.assertNotEqual(self.pe.canonical(self.x),   self.pe.canonical(self.y))
		self.assertNotEqual(self.pe.canonical(self.z),   self.pe.canonical(self.w))
		self.assertEqual(self.pe.canonical(self.x),   self.pe.canonical(self.z))



class TestPathEquivalenceOps(TestEquivilenceBase):
	def testIntersection(self):
		pe1 = path.PathEquivalence(self.canonical.fieldExpr)
		pe1.union(self.a, self.b, self.c)
		pe1.union(self.x, self.y, self.z)

		pe2 = path.PathEquivalence(self.canonical.fieldExpr)
		pe2.union(self.a, self.b, self.z)
		pe2.union(self.x, self.y, self.c)

		pe3 = pe1.setIntersection(pe2)

		self.assertEqual(pe3.canonical(self.a),      pe3.canonical(self.b))
		self.assertNotEqual(pe3.canonical(self.a),   pe3.canonical(self.c))
		self.assertNotEqual(pe3.canonical(self.a),   pe3.canonical(self.x))
		self.assertNotEqual(pe3.canonical(self.a),   pe3.canonical(self.y))
		self.assertNotEqual(pe3.canonical(self.a),   pe3.canonical(self.z))

		self.assertEqual(pe3.canonical(self.x),      pe3.canonical(self.y))
		self.assertNotEqual(pe3.canonical(self.x),   pe3.canonical(self.z))
		self.assertNotEqual(pe3.canonical(self.x),   pe3.canonical(self.a))
		self.assertNotEqual(pe3.canonical(self.x),   pe3.canonical(self.b))
		self.assertNotEqual(pe3.canonical(self.x),   pe3.canonical(self.c))
		

	def testIntersection(self):
		pe1 = path.PathEquivalence(self.canonical.fieldExpr)
		pe1.union(self.a, self.b)
		pe1.union(self.x, self.y)

		pe2 = path.PathEquivalence(self.canonical.fieldExpr)
		pe2.union(self.a, self.c)
		pe2.union(self.x, self.z)

		pe3 = pe1.setUnion(pe2)

		self.assertEqual(pe3.canonical(self.a),      pe3.canonical(self.b))
		self.assertEqual(pe3.canonical(self.a),      pe3.canonical(self.c))
		self.assertNotEqual(pe3.canonical(self.a),   pe3.canonical(self.x))
		self.assertNotEqual(pe3.canonical(self.a),   pe3.canonical(self.y))
		self.assertNotEqual(pe3.canonical(self.a),   pe3.canonical(self.z))

		self.assertEqual(pe3.canonical(self.x),      pe3.canonical(self.y))
		self.assertEqual(pe3.canonical(self.x),      pe3.canonical(self.z))
		self.assertNotEqual(pe3.canonical(self.x),   pe3.canonical(self.a))
		self.assertNotEqual(pe3.canonical(self.x),   pe3.canonical(self.b))
		self.assertNotEqual(pe3.canonical(self.x),   pe3.canonical(self.c))
