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

		self.c0 = self.manager.condition(0)
		self.c1 = self.manager.condition(1)

	def testAnd(self):
		a = self.manager.tree(self.c0, True, False)
		b = self.manager.tree(self.c1, True, False)
		c = self.manager.tree(self.c1, a, False)

		andresult = self.manager.apply(lambda l, r: l & r, a, b)

		self.assert_(andresult is c)

	def testOr(self):
		a = self.manager.tree(self.c0, True, False)
		b = self.manager.tree(self.c1, True, False)
		d = self.manager.tree(self.c1, True, a)

		orresult  = self.manager.apply(lambda l, r: l | r, a, b)

		self.assert_(orresult is d)