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

import analysis.cpa
import application.makefile
from decompiler.programextractor import extractProgram


from util.application.console import Console
from application.context import CompilerContext

from decompiler.programextractor import Extractor
from util.python import replaceGlobals

class TestCPA(unittest.TestCase):
	def assertIn(self, first, second, msg=None):
		"""Fail if the one object is not in the other, using the "in" operator.
		"""
		if first not in second:
			raise self.failureException, (msg or '%r not in %r' % (first, second))

	def assertLocalRefTypes(self, lcl, types):
		refs   = lcl.annotation.references[0]

		# There's one reference returned, and it's an integer.
		self.assertEqual(len(refs), len(types))
		for ref in refs:
			self.assertIn(ref.xtype.obj.type, types)

	def testAdd(self):
		def func(a, b):
			return 2*a+b

		# Prevent leakage?
		func = replaceGlobals(func, {})

		# TODO mock console?
		compiler = CompilerContext(Console())

		interface = application.makefile.InterfaceDeclaration()

		interface.func.append((func,
			(application.makefile.ExistingWrapper(3), application.makefile.ExistingWrapper(5))
			))

		compiler.interface = interface

		extractProgram(compiler)
		result = analysis.cpa.evaluate(compiler)

		# Check argument and return types
		funcobj, funcast = compiler.extractor.getObjectCall(func)
		types = set([compiler.extractor.getObject(int)])

		for param in funcast.codeparameters.params:
			self.assertLocalRefTypes(param, types)

		for param in funcast.codeparameters.returnparams:
			self.assertLocalRefTypes(param, types)
