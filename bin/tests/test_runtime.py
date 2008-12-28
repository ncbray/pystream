from __future__ import absolute_import

import unittest

from streamRT import *

class TestFunctionKernel(unittest.TestCase):
	def setUp(self):
		self.a = stream([1, 2, 3, 4])
		self.b = stream([2, 3, 4, 5])
		self.c = stream([0, 0, 0])

		@kernel
		def add(a, b):
			return a+b

		self.kernel = add

	def testPureUniform(self):
		out = self.kernel(1, 2)
		self.assertEqual(out, 3)

	def testPureStream(self):
		out = self.kernel(self.a, self.b)
		self.assertEqual(out.elements, [3, 5, 7, 9])

	def testMixed(self):
		out = self.kernel(self.a, 3)
		self.assertEqual(out.elements, [4, 5, 6, 7])

	def testMismatched(self):
		self.assertRaises(StreamMismatchError, self.kernel, self.a, self.c)

class TestSimpleKernel(unittest.TestCase):
	def setUp(self):
		self.a = stream([1, 2, 3, 4])
		self.b = stream([2, 3, 4, 5])
		self.c = stream([0, 0, 0])

	def testStreamAdd(self):
		out = self.a+self.b
		self.assertEqual(out.elements, [3, 5, 7, 9])

	def testMixedAdd(self):
		out = self.a+1
		self.assertEqual(out.elements, [2, 3, 4, 5])

	def testMixedRAdd(self):
		out = 1+self.a
		self.assertEqual(out.elements, [2, 3, 4, 5])



	def testStreamSub(self):
		out = self.a-self.b
		self.assertEqual(out.elements, [-1, -1, -1, -1])

	def testMixedSub(self):
		out = self.a-1
		self.assertEqual(out.elements, [0, 1, 2, 3])

	def testMixedRSub(self):
		out = 1-self.a
		self.assertEqual(out.elements, [0, -1, -2, -3])

	def testStreamMul(self):
		out = self.a*self.b
		self.assertEqual(out.elements, [2, 6, 12, 20])
		
class TestKernelMethod(unittest.TestCase):
	def setUp(self):
		self.a = stream([1, 2, 3, 4])


		class RunningSum(object):
			def __init__(self, inital=0):
				self.total = inital

			@kernel
			def accumulate(self, amt):
				self.total += amt

		self.inst = RunningSum()

	def testmethod(self):
		self.assertEqual(self.inst.total, 0)
		self.inst.accumulate(self.a)
		self.inst.accumulate(self.a)
		self.assertEqual(self.inst.total, 20)



class TestUniformKernel(unittest.TestCase):
	def setUp(self):
		self.index = stream([(0, 0), (2, 4), (3, 1)])
		self.values = stream([1, 2, 3, 4, 5])

		@kernel.roles(values=uniform)
		def doindex(index, values):
			a, b = index
			return values[a] + values[b]

		self.kernel = doindex

	def testPureStream(self):
		out = self.kernel(self.index, self.values)
		self.assertEqual(out.elements, [2, 8, 6])
