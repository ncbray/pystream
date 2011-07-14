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

import application.context
#from decompiler import decompile
from decompiler.programextractor import Extractor

from cStringIO import StringIO
from language.python.simplecodegen import SimpleCodeGen

def compileF(s, g=None):
	l = {}
	eval(compile(s, '<string>', 'exec'), g, l)
	assert len(l) == 1
	return l.values()[0]

def generateCode(func, trace):
	compiler = application.context.CompilerContext(None)
	extractor = Extractor(compiler)
	compiler.extractor = extractor

	f = extractor.decompileFunction(func, trace)
	#f = decompile(func, trace)

	sio = StringIO()
	scg = SimpleCodeGen(sio)
	scg.process(f)
	return sio.getvalue()

# How do I prevent it from being a test?
class TestDecompiler(unittest.TestCase):
	s = ""
	inputs = [[]]
	trace = False


	def setUp(self):
		if self.s:
			self.s = self.s.strip()
			self.f = compileF(self.s)
			self.decompCode = generateCode(self.f, self.trace)

			try:
				self.df = compileF(self.decompCode)
			except SyntaxError:
				print
				print "Generated code with malformed syntax."
				print
				print self.decompCode
				print
				raise

	def testInputs(self):
		if self.s:
			try:
				for inp in self.inputs:
					actual = self.df(*inp)
					expected = self.f(*inp)

					self.assertEqual(actual, expected)

			except:
				print "-TRACE"*5
				print self.decompCode

				raise

class Dummy(object):
	pass
