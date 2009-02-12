from __future__ import absolute_import
import unittest

import analysis.cpa
from common.compilerconsole import CompilerConsole
from decompiler.programextractor import Extractor
from util import replaceGlobals

from stubs import makeStubs

class TestCPA(unittest.TestCase):
	def assertIn(self, first, second, msg=None):
		"""Fail if the one object is not in the other, using the "in" operator.
		"""
		if first not in second:
			raise self.failureException, (msg or '%r not in %r' % (first, second))


	def assertLocalRefTypes(self, finfo, lcl, types):
		self.assertIn(lcl, finfo.localInfos)
		linfo  = finfo.localInfos[lcl].merged
		refs   = linfo.references

		# There's one reference returned, and it's an integer.
		self.assertEqual(len(refs), len(types))
		for ref in refs:
			self.assertIn(ref.xtype.obj.type, types)


	def processFunc(self, func):

		func = replaceGlobals(func, {})

		funcobj = self.extractor.getObject(func)

		self.extractor.ensureLoaded(funcobj)
		funcast = self.extractor.getCall(funcobj)

		return func, funcast, funcobj


	def testAdd(self):
		self.extractor = Extractor(verbose=False)
		makeStubs(self.extractor)

		def func(a, b):
			return 2*a+b

		func, funcast, funcobj = self.processFunc(func)

		for paramname in funcast.parameternames:
			self.assertEqual(type(paramname), str)

		a = self.extractor.getObject(3)
		b = self.extractor.getObject(5)

		result = analysis.cpa.evaluate(CompilerConsole(), self.extractor, [(funcast, funcobj, (a, b))])

		finfo  = result.db.functionInfo(funcast)
		types = set((self.extractor.getObject(int),))

		for param in funcast.parameters:
			self.assertLocalRefTypes(finfo, param, types)

		self.assertLocalRefTypes(finfo, funcast.returnparam, types)
