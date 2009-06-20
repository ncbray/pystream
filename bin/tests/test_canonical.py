from __future__ import absolute_import

import unittest

from analysis.fsdf import canonicalset, canonicaltree

class TestCanonicalSet(unittest.TestCase):
	def setUp(self):
		self.manager = canonicalset.CanonicalSetManager()

	def testIs(self):
		a = self.manager.canonical(('a', 'b'))
		b = self.manager.canonical(['b', 'a'])
		self.assert_(a is b)
		self.assert_('a' in a)
		self.assert_('b' in a)

	def testUnion(self):
		a = self.manager.canonical((1, 2))
		b = self.manager.canonical((2, 3))
		c = self.manager.canonical((1, 2, 3))

		self.assert_(self.manager.union(a, b) is c)

	def testIntersection(self):
		a = self.manager.canonical((1, 2))
		b = self.manager.canonical((2, 3))
		c = self.manager.canonical((2,))

		self.assert_(self.manager.intersection(a, b) is c)



class TestCanonicalTree(unittest.TestCase):
	def setUp(self):
		self.manager = canonicaltree.CanonicalTreeManager()

		self.c0 = self.manager.condition(0, 2)
		self.c1 = self.manager.condition(1, 2)
		self.c2 = self.manager.condition(2, 3)


		self.andFunc = canonicaltree.BinaryTreeFunction(self.manager, lambda l, r: l & r,
			symmetric=True, stationary=True, identity=True, null=False)

		self.orFunc  = canonicaltree.BinaryTreeFunction(self.manager, lambda l, r: l | r,
			symmetric=True, stationary=True, identity=False, null=True)


	def testSimpleAnd(self):
		a = self.manager.tree(self.c2, (True, False, True))
		b = self.manager.tree(self.c2, (True, False, False))
		c = self.manager.tree(self.c2, (True, False, False))

		result = self.andFunc.apply(a, b)
		self.assert_(result is c)

	def testSimpleOr(self):
		a = self.manager.tree(self.c2, (True, False, True))
		b = self.manager.tree(self.c2, (True, False, False))
		c = self.manager.tree(self.c2, (True, False, True))

		result = self.orFunc.apply(a, b)
		self.assert_(result is c)

	def testAnd(self):
		a = self.manager.tree(self.c0, (True, False))
		b = self.manager.tree(self.c1, (True, False))
		c = self.manager.tree(self.c1, (a, False))

		result = self.andFunc.apply(a, b)
		self.assert_(result is c)

	def testOr(self):
		a = self.manager.tree(self.c0, (True, False))
		b = self.manager.tree(self.c1, (True, False))
		c = self.manager.tree(self.c1, (True, a))

		result = self.orFunc.apply(a, b)
		self.assert_(result is c)


	def testITE1(self):
		f = self.manager.tree(self.c1, (True, False))
		a = self.manager.tree(self.c0, (True, False))
		b = self.manager.tree(self.c0, (False, True))
		c = self.manager.tree(self.c1, (a, b))

		result = self.manager.ite(f, a, b)
		self.assert_(result is c)


	def testITE2(self):
		f = self.manager.tree(self.c0, (True, False))
		a = self.manager.tree(self.c1, (True, False))
		b = self.manager.tree(self.c1, (False, True))
		c = self.manager.tree(self.c1, (self.manager.tree(self.c0, (True, False)),  self.manager.tree(self.c0, (False, True))))

		result = self.manager.ite(f, a, b)
		self.assert_(result is c)

	def testITE3(self):
		f = self.manager.tree(self.c0, (True, False))
		a = False
		b = True
		c = self.manager.tree(self.c0, (False, True))

		result = self.manager.ite(f, a, b)
		self.assert_(result is c)


	def testRestrict1(self):
		a = self.manager.tree(self.c0, (True, False))
		b = self.manager.tree(self.c0, (False, True))
		d = self.manager.tree(self.c1, (a, b))

		c = self.manager.tree(self.c1, (True, False))

		result = self.manager.restrict(d, {self.c0:0})
		self.assert_(result is c)


	def testRestrict2(self):
		a = self.manager.tree(self.c0, (True, False))
		b = self.manager.tree(self.c0, (False, True))
		d = self.manager.tree(self.c1, (a, b))

		c = self.manager.tree(self.c1, (False, True))

		result = self.manager.restrict(d, {self.c0:1})
		self.assert_(result is c)