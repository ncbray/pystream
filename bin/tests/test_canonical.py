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
		self.conditions = canonicaltree.ConditionManager()
		self.manager    = canonicaltree.BoolManager(self.conditions)

		self.c0 = self.conditions.condition(0, [0, 1])
		self.c1 = self.conditions.condition(1, [0, 1])
		self.c2 = self.conditions.condition(2, [0, 1, 2])

		self.t  = self.manager.true
		self.f  = self.manager.false

	def testSimpleAnd(self):
		t, f = self.t, self.f
		a = self.manager.tree(self.c2, (t, f, t))
		b = self.manager.tree(self.c2, (t, f, f))
		c = self.manager.tree(self.c2, (t, f, f))

		result = self.manager.and_(a, b)
		self.assert_(result is c)

	def testSimpleOr(self):
		t, f = self.t, self.f
		a = self.manager.tree(self.c2, (t, f, t))
		b = self.manager.tree(self.c2, (t, f, f))
		c = self.manager.tree(self.c2, (t, f, t))

		result = self.manager.or_(a, b)
		self.assert_(result is c)

	def testAnd(self):
		t, f = self.t, self.f
		a = self.manager.tree(self.c0, (t, f))
		b = self.manager.tree(self.c1, (t, f))
		c = self.manager.tree(self.c1, (a, f))

		result = self.manager.and_(a, b)
		self.assert_(result is c, (result, c))

	def testOr(self):
		t, f = self.t, self.f
		a = self.manager.tree(self.c0, (t, f))
		b = self.manager.tree(self.c1, (t, f))
		c = self.manager.tree(self.c1, (t, a))

		result = self.manager.or_(a, b)
		self.assert_(result is c)


	def testITE1(self):
		t, f = self.t, self.f

		d = self.manager.tree(self.c1, (t, f))
		a = self.manager.tree(self.c0, (t, f))
		b = self.manager.tree(self.c0, (f, t))
		c = self.manager.tree(self.c1, (a, b))

		result = self.manager.ite(d, a, b)
		self.assert_(result is c)


	def testITE2(self):
		t, f = self.t, self.f
		d = self.manager.tree(self.c0, (t, f))
		a = self.manager.tree(self.c1, (t, f))
		b = self.manager.tree(self.c1, (f, t))
		c = self.manager.tree(self.c1, (self.manager.tree(self.c0, (t, f)),  self.manager.tree(self.c0, (f, t))))

		result = self.manager.ite(d, a, b)
		self.assert_(result is c)

	def testITE3(self):
		t, f = self.t, self.f
		d = self.manager.tree(self.c0, (t, f))
		a = f
		b = t
		c = self.manager.tree(self.c0, (f, t))

		result = self.manager.ite(d, a, b)
		self.assert_(result is c)


	def testRestrict1(self):
		t, f = self.t, self.f
		a = self.manager.tree(self.c0, (t, f))
		b = self.manager.tree(self.c0, (f, t))
		d = self.manager.tree(self.c1, (a, b))

		c = self.manager.tree(self.c1, (t, f))

		result = self.manager.restrict(d, {self.c0:0})
		self.assert_(result is c)


	def testRestrict2(self):
		t, f = self.t, self.f
		a = self.manager.tree(self.c0, (t, f))
		b = self.manager.tree(self.c0, (f, t))
		d = self.manager.tree(self.c1, (a, b))

		c = self.manager.tree(self.c1, (f, t))

		result = self.manager.restrict(d, {self.c0:1})
		self.assert_(result is c)


	def testSimplify1(self):
		t, f = self.t, self.f
		a = self.manager.tree(self.c0, (t, f))
		b = self.manager.tree(self.c0, (f, t))
		d = self.manager.tree(self.c1, (a, b))

		c = t

		result = self.manager.simplify(d, d, f)
		self.assert_(result, c)


	def testSimplify2(self):
		t, f = self.t, self.f
		a = self.manager.tree(self.c0, (t, f))
		b = self.manager.tree(self.c0, (f, t))
		d = self.manager.tree(self.c1, (a, b))

		domain = self.manager.tree(self.c0, (t, f))

		c =  self.manager.tree(self.c1, (t, f))

		result = self.manager.simplify(domain, d, f)
		self.assert_(result, c)


	def testSimplify3(self):
		t, f = self.t, self.f
		a = self.manager.tree(self.c0, (t, f))
		b = self.manager.tree(self.c0, (f, t))
		d = self.manager.tree(self.c1, (a, b))

		domain = self.manager.tree(self.c1, (t, f))

		c =  self.manager.tree(self.c0, (t, f))

		result = self.manager.simplify(domain, d, f)
		self.assert_(result, c)

	def testSimplify4(self):
		t, f = self.t, self.f
		a      = self.manager.tree(self.c2, (t, f, t))
		domain = self.manager.tree(self.c2, (t, t, f))
		c      = self.manager.tree(self.c2, (t, f, f))

		result = self.manager.simplify(domain, a, f)
		self.assert_(result, c)

	def testSimplify5(self):
		t, f = self.t, self.f
		a      = self.manager.tree(self.c2, (f, t, f))
		domain = self.manager.tree(self.c2, (t, f, t))
		c      =  f

		result = self.manager.simplify(domain, a, f)
		self.assert_(result, c)

	def testSimplifyDefault(self):
		t, f = self.t, self.f
		a      = self.manager.tree(self.c2, (f, t, f))
		domain = self.manager.tree(self.c2, (t,  t, f))
		c      = self.manager.tree(self.c2, (f, t, t))

		result = self.manager.simplify(domain, a, t)
		self.assert_(result, c)


class TestCanonicalSet(unittest.TestCase):
	def setUp(self):
		self.conditions  = canonicaltree.ConditionManager()
		self.boolManager = canonicaltree.BoolManager(self.conditions)
		self.setManager  = canonicaltree.SetManager()

		self.c0 = self.conditions.condition(0, [0, 1])
		self.c1 = self.conditions.condition(1, [0, 1])
		self.c2 = self.conditions.condition(2, [0, 1, 2])

	def testSimplify(self):
		zero = self.setManager.empty
		one  = self.setManager.leaf((1,))
		two  = self.setManager.leaf((1,2))

		true  = self.boolManager.true
		false = self.boolManager.false

		domain  = self.boolManager.tree(self.c2, (false, true, false))
		tree     = self.setManager.tree(self.c2, (one, two, zero))
		default  = zero
		expected = two

		result = self.setManager.simplify(domain, tree, default)
		self.assert_(result is expected, (result, expected))