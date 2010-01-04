from __future__ import absolute_import

import unittest

import util.lattice

class TestFunctionKernel(unittest.TestCase):
	def setUp(self):
		a = 'a'
		b = 'b'
		c = 'c'
		d = 'd'
		e = 'e'
		f = 'f'

		self.G = {a:(b,c,), b:(d,f,), c:(d,e,), d:(), e:(f,), f:()}

		self.lattice = util.lattice.Lattice(self.G, a)

	def testGLB1(self):
		glb = self.lattice.glb('b', 'c')
		self.assertEqual(glb, ('a',))

	def testGLB2(self):
		glb = self.lattice.glb('b', 'e')
		self.assertEqual(glb, ('a',))


	def testGLB3(self):
		glb = self.lattice.glb('d', 'e')
		self.assertEqual(glb, ('c',))

	def testGLB4(self):
		glb = self.lattice.glb('d', 'f')
		self.assertEqual(glb, ('b','c',))

	def testLUB1(self):
		lub = self.lattice.lub('b', 'c')
		self.assertEqual(lub, ('d','f'))

	def testLUB2(self):
		lub = self.lattice.lub('b', 'e')
		self.assertEqual(lub, ('f',))
