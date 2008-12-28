from __future__ import absolute_import

import unittest
from analysis.bdddatalog import relational

class TestRelational(unittest.TestCase):
	def testLogical(self):
		a = relational.LogicalDomain('temp0', 4)
		b = relational.LogicalDomain('temp1', 5)

		self.assertEqual(a.numbits, 2)

		for i in range(4):
			self.assert_(a.contains(i))
		for i in range(4, 8):
			self.assert_(not a.contains(i))

		self.assertEqual(b.numbits, 3)
		for i in range(5):
			self.assert_(b.contains(i))
		for i in range(5, 8):
			self.assert_(not b.contains(i))

	def testRestrict(self):
		a = relational.LogicalDomain('temp0', 4)
		b = relational.LogicalDomain('temp1', 5)

		a0 = a.physical(0, 1)
		b0 = b.physical(a.numbits, 1)

		fields = (('a', a0), ('b', b0))
		r = relational.Relation(fields)

		self.assert_(r.isFalse())
		self.assert_(r.maybeFalse())
		self.assert_(not r.maybeEither())
		self.assert_(not r.maybeTrue())
		self.assert_(not r.isTrue())

		r |= r.entry(a=3, b=4)

		self.assert_(not r.isFalse())
		self.assert_(r.maybeFalse())
		self.assert_(r.maybeEither())
		self.assert_(r.maybeTrue())
		self.assert_(not r.isTrue())


		r34 = r.restrict(a=3, b=4)

		self.assert_(not r34.isFalse())
		self.assert_(not r34.maybeFalse())
		self.assert_(not r34.maybeEither())
		self.assert_(r34.maybeTrue())
		self.assert_(r34.isTrue())
		
		self.assertEqual(r34.attributes, ())

		r4 = r.restrict(b=4)

		self.assert_(not r4.isFalse())
		self.assert_(r4.maybeFalse())
		self.assert_(r4.maybeEither())
		self.assert_(r4.maybeTrue())
		self.assert_(not r4.isTrue())

		self.assertEqual(r4.enumerateList(), [(3,)])
		self.assertEqual(r4.attributes, (('a', a0),))

class TestRelationalOps(unittest.TestCase):
	def setUp(self):
		d = relational.LogicalDomain('temp', 4)
		self.d0 = d.physical(0, 3)
		self.d1 = d.physical(1, 3)
		self.d2 = d.physical(2, 3)

		t0 = (('a', self.d0), ('b', self.d1))
		t1 = (('b', self.d1), ('c', self.d2))

		self.a = relational.Relation(t0)
		self.b = relational.Relation(t0)
		self.c = relational.Relation(t1)

	def init(self, rel, data):
		names = [name for name, domain in rel.attributes]
		lut = {}
		
		for d in data:
			for name, value in zip(names, d):
				lut[name] = value
			rel |= rel.entry(**lut)	
		return rel

	def testUnion(self):
		adata = [(0, 0), (3, 0)]
		bdata = [(0, 0), (1, 2)]

		result = set(adata).union(set(bdata))
					  
		a = self.init(self.a, adata)
		b = self.init(self.b, bdata)

		c = a.union(b)

		self.assertEqual(set(c.enumerateList()), result)
		self.assertEqual(c.attributes, self.a.attributes)

	def testJoin(self):
		adata = [(0, 0), (3, 1)]
		bdata = [(0, 0), (1, 2), (1, 0)]
		result = [(0, 0, 0), (3, 1, 2), (3, 1, 0)]
					  
		a = self.init(self.a, adata)
		b = self.init(self.c, bdata)

		c = a.join(b)

		self.assertEqual(set(c.enumerateList()), set(result))

		t = (('a', self.d0), ('b', self.d1), ('c', self.d2))
		self.assertEqual(c.attributes, t)

	def testCompose(self):
		adata = [(0, 0), (3, 1), (3, 2)]
		bdata = [(0, 0), (1, 2), (1, 0), (2, 0)]
		result = [(0, 0), (3, 2), (3, 0)]
					  
		a = self.init(self.a, adata)
		b = self.init(self.c, bdata)

		c = a.compose(b)

		self.assertEqual(set(c.enumerateList()), set(result))

		t = (('a', self.d0), ('c', self.d2))
		self.assertEqual(c.attributes, t)

	def testForget(self):
		adata = [(0, 0), (3, 1), (3, 2)]
		result = [(0,), (3,)]
					  
		a = self.init(self.a, adata)

		c = a.forget('b')


		t = (('a', self.d0),)
		self.assertEqual(c.attributes, t)
		self.assertEqual(set(c.enumerateList()), set(result))


	def testInvert(self):
		adata = [(1,)]
		result = [(0,), (2,), (3,)]

		self.a = self.a.forget('b')
		a = self.init(self.a, adata)
		c = a.invert()

		t = a.attributes
		self.assertEqual(c.attributes, t)
		self.assertEqual(set(c.enumerateList()), set(result))

	# TODO test rename, relocate, and modify?

if __name__ == '__main__':
	unittest.main()
