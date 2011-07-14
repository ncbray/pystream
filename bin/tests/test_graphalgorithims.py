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

import unittest

from util.graphalgorithim import exclusiongraph

class TestExclusionGraph(unittest.TestCase):
	def forward(self, node):
		return self.G.get(node, ())

	def exclusive(self, node):
		return True

	def build(self, G, roots):
		self.G = G
		self.roots = roots

		self.exg = exclusiongraph.build(roots, self.forward, self.exclusive)

	def argString(self, args):
		return ", ".join([repr(arg) for arg in args])

	def assertExclusive(self, *args):
		self.assert_(self.exg.mutuallyExclusive(*args), "%s should be mutually exclusive" % self.argString(args))

	def assertNotExclusive(self, *args):
		self.failIf(self.exg.mutuallyExclusive(*args), "%s should not be mutually exclusive" % self.argString(args))


	def test1(self):
		self.build({0:[1, 2], 1:[3], 2:[3]}, [0])

		self.assertNotExclusive(0, 1)
		self.assertNotExclusive(0, 2)
		self.assertNotExclusive(0, 3)
		self.assertExclusive(1, 2)
		self.assertNotExclusive(1, 3)
		self.assertNotExclusive(2, 3)

		self.assertNotExclusive(0, 1, 2)
		self.assertNotExclusive(0, 1, 3)
		self.assertNotExclusive(0, 2, 3)
		self.assertNotExclusive(1, 2, 3)
		self.assertNotExclusive(0, 1, 2, 3)


	def test2(self):
		self.build({0:[1, 2], 1:[3, 4]}, [0])

		self.assertNotExclusive(0, 1)
		self.assertNotExclusive(0, 2)
		self.assertNotExclusive(0, 3)
		self.assertNotExclusive(0, 4)

		self.assertExclusive(1, 2)
		self.assertExclusive(3, 4)

		self.assertExclusive(2, 3)
		self.assertExclusive(2, 4)
		self.assertExclusive(2, 3, 4)


	def test3(self):
		self.build({0:[1, 2], 1:[3, 4],  2:[5, 6], 3:[7], 4:[7], 5:[8], 6:[8], 7:[9], 8:[9]}, [0])

		self.assertExclusive(1, 2)
		self.assertExclusive(3, 4)
		self.assertExclusive(5, 6)
		self.assertExclusive(7, 8)

		self.assertExclusive(3, 4, 5, 6)
		self.assertExclusive(3, 4, 8)
		self.assertExclusive(5, 6, 7)

		self.assertNotExclusive(5, 6, 8)
		self.assertNotExclusive(3, 4, 7)

		self.assertExclusive(1, 8)
		self.assertExclusive(2, 7)

		self.assertNotExclusive(1, 7)
		self.assertNotExclusive(2, 8)

	def test4(self):
		self.build({0:[1, 2, 3], 1:[3],  2:[3]}, [0])

		self.assertExclusive(1, 2)
		self.assertNotExclusive(1, 3)
		self.assertNotExclusive(2, 3)
