from __future__ import absolute_import

import unittest

import util.compressedset

class TestCompressedSetUnion(unittest.TestCase):
	def testUnion1(self):
		s = set((1, 2))
		t = set((2, 3))
		expected = set((1, 2, 3))
		result = util.compressedset.union(s, t)
		self.assertEqual(result, expected)

	def testUnion2(self):
		s = set((1, 2))
		t = util.compressedset.nullSet
		expected = set((1, 2))
		result = util.compressedset.union(s, t)
		self.assertEqual(result, expected)

	def testUnion3(self):
		s = util.compressedset.nullSet
		t = set((1, 2))
		expected = set((1, 2))
		result = util.compressedset.union(s, t)
		self.assertEqual(result, expected)


	def testInplaceUnion1(self):
		s = set((1, 2))
		t = set((2, 3))
		expected = set((1, 2, 3))
		result, changed = util.compressedset.inplaceUnion(s, t)

		self.assertEqual(changed, True)
		self.assertEqual(result, expected)

		self.assertEqual(s, expected)
		self.assertEqual(t, set((2, 3)))

	def testInplaceUnion2(self):
		s = set((1, 2))
		t = util.compressedset.nullSet
		expected = set((1, 2))
		result, changed = util.compressedset.inplaceUnion(s, t)

		self.assertEqual(changed, False)
		self.assertEqual(result, expected)

		self.assertEqual(s, set((1,2)))
		self.assertEqual(t, util.compressedset.nullSet)

	def testInplaceUnion3(self):
		s = util.compressedset.nullSet
		t = set((1, 2))
		expected = set((1, 2))
		result, changed = util.compressedset.inplaceUnion(s, t)

		self.assertEqual(changed, True)
		self.assertEqual(result, expected)

		self.assertEqual(s, util.compressedset.nullSet)
		self.assertEqual(t, set((1,2)))



class TestCompressedSetIntersection(unittest.TestCase):
	def testIntersection1(self):
		s = set((1, 2))
		t = set((2, 3))
		expected = set((2,))
		result = util.compressedset.intersection(s, t)
		self.assertEqual(result, expected)

	def testIntersection2(self):
		s = set((1, 2))
		t = util.compressedset.nullSet
		expected = util.compressedset.nullSet
		result = util.compressedset.intersection(s, t)
		self.assertEqual(result, expected)

	def testIntersection3(self):
		s = util.compressedset.nullSet
		t = set((1, 2))
		expected = util.compressedset.nullSet
		result = util.compressedset.intersection(s, t)
		self.assertEqual(result, expected)


	def testInplaceIntersection1(self):
		s = set((1, 2))
		t = set((2, 3))
		expected = set((2,))
		result, changed = util.compressedset.inplaceIntersection(s, t)

		self.assertEqual(changed, True)
		self.assertEqual(result, expected)

		self.assertEqual(s, expected)
		self.assertEqual(t, set((2, 3)))

	def testInplaceIntersection2(self):
		s = set((1, 2))
		t = util.compressedset.nullSet
		expected = util.compressedset.nullSet
		result, changed = util.compressedset.inplaceIntersection(s, t)

		self.assertEqual(changed, True)
		self.assertEqual(result, expected)

		self.assertEqual(s, set((1,2)))
		self.assertEqual(t, util.compressedset.nullSet)

	def testInplaceIntersection3(self):
		s = util.compressedset.nullSet
		t = set((1, 2))
		expected = util.compressedset.nullSet
		result, changed = util.compressedset.inplaceIntersection(s, t)

		self.assertEqual(changed, False)
		self.assertEqual(result, expected)

		self.assertEqual(s, util.compressedset.nullSet)
		self.assertEqual(t, set((1,2)))
