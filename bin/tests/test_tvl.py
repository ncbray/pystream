from __future__ import absolute_import
import unittest

import util.tvl as tvl

class TestTVLTruth(unittest.TestCase):
	def testTVLTrue(self):
		self.assertEqual(tvl.TVLTrue.mustBeTrue(),  True)
		self.assertEqual(tvl.TVLTrue.maybeTrue(),   True)
		self.assertEqual(tvl.TVLTrue.maybeFalse(),  False)
		self.assertEqual(tvl.TVLTrue.mustBeFalse(), False)
		
		self.assertRaises(TypeError, bool, tvl.TVLTrue)
		

	def testTVLFalse(self):
		self.assertEqual(tvl.TVLFalse.mustBeTrue(),  False)
		self.assertEqual(tvl.TVLFalse.maybeTrue(),   False)
		self.assertEqual(tvl.TVLFalse.maybeFalse(),  True)
		self.assertEqual(tvl.TVLFalse.mustBeFalse(), True)
		
		self.assertRaises(TypeError, bool, tvl.TVLFalse)
		
	def testTVLMaybe(self):
		self.assertEqual(tvl.TVLMaybe.mustBeTrue(),  False)
		self.assertEqual(tvl.TVLMaybe.maybeTrue(),   True)
		self.assertEqual(tvl.TVLMaybe.maybeFalse(),  True)
		self.assertEqual(tvl.TVLMaybe.mustBeFalse(), False)
		
		self.assertRaises(TypeError, bool, tvl.TVLMaybe)
		

class TestTVLInvert(unittest.TestCase):
	def testTVLTrue(self):
		self.assertEqual(~tvl.TVLTrue, tvl.TVLFalse)

	def testTVLFalse(self):
		self.assertEqual(~tvl.TVLFalse, tvl.TVLTrue)

	def testTVLMaybe(self):
		self.assertEqual(~tvl.TVLMaybe, tvl.TVLMaybe)
		
class TestTVLAnd(unittest.TestCase):
	def testTVLTrue(self):
		self.assertEqual(tvl.TVLTrue&tvl.TVLTrue,  tvl.TVLTrue)
		self.assertEqual(tvl.TVLTrue&tvl.TVLFalse, tvl.TVLFalse)
		self.assertEqual(tvl.TVLTrue&tvl.TVLMaybe, tvl.TVLMaybe)

	def testTVLFalse(self):
		self.assertEqual(tvl.TVLFalse&tvl.TVLTrue,  tvl.TVLFalse)
		self.assertEqual(tvl.TVLFalse&tvl.TVLFalse, tvl.TVLFalse)
		self.assertEqual(tvl.TVLFalse&tvl.TVLMaybe, tvl.TVLFalse)

	def testTVLMaybe(self):
		self.assertEqual(tvl.TVLMaybe&tvl.TVLTrue,  tvl.TVLMaybe)
		self.assertEqual(tvl.TVLMaybe&tvl.TVLFalse, tvl.TVLFalse)
		self.assertEqual(tvl.TVLMaybe&tvl.TVLMaybe, tvl.TVLMaybe)

class TestTVLOr(unittest.TestCase):
	def testTVLTrue(self):
		self.assertEqual(tvl.TVLTrue|tvl.TVLTrue,  tvl.TVLTrue)
		self.assertEqual(tvl.TVLTrue|tvl.TVLFalse, tvl.TVLTrue)
		self.assertEqual(tvl.TVLTrue|tvl.TVLMaybe, tvl.TVLTrue)

	def testTVLFalse(self):
		self.assertEqual(tvl.TVLFalse|tvl.TVLTrue,  tvl.TVLTrue)
		self.assertEqual(tvl.TVLFalse|tvl.TVLFalse, tvl.TVLFalse)
		self.assertEqual(tvl.TVLFalse|tvl.TVLMaybe, tvl.TVLMaybe)

	def testTVLMaybe(self):
		self.assertEqual(tvl.TVLMaybe|tvl.TVLTrue,  tvl.TVLTrue)
		self.assertEqual(tvl.TVLMaybe|tvl.TVLFalse, tvl.TVLMaybe)
		self.assertEqual(tvl.TVLMaybe|tvl.TVLMaybe, tvl.TVLMaybe)

class TestTVLXor(unittest.TestCase):
	def testTVLTrue(self):
		self.assertEqual(tvl.TVLTrue^tvl.TVLTrue,  tvl.TVLFalse)
		self.assertEqual(tvl.TVLTrue^tvl.TVLFalse, tvl.TVLTrue)
		self.assertEqual(tvl.TVLTrue^tvl.TVLMaybe, tvl.TVLMaybe)

	def testTVLFalse(self):
		self.assertEqual(tvl.TVLFalse^tvl.TVLTrue,  tvl.TVLTrue)
		self.assertEqual(tvl.TVLFalse^tvl.TVLFalse, tvl.TVLFalse)
		self.assertEqual(tvl.TVLFalse^tvl.TVLMaybe, tvl.TVLMaybe)

	def testTVLMaybe(self):
		self.assertEqual(tvl.TVLMaybe^tvl.TVLTrue,  tvl.TVLMaybe)
		self.assertEqual(tvl.TVLMaybe^tvl.TVLFalse, tvl.TVLMaybe)
		self.assertEqual(tvl.TVLMaybe^tvl.TVLMaybe, tvl.TVLMaybe)