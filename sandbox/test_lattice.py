# Copyright 2011 Nicholas Bray
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
