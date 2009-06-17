from __future__ import absolute_import

import unittest

import common.compilercontext
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
	compiler = common.compilercontext.CompilerContext(None)
	extractor = Extractor(compiler)
	compiler.extractor = extractor

	f = extractor.decompileFunction(func, trace)
	#f = decompile(func, trace)

	sio = StringIO()
	scg = SimpleCodeGen(sio)
	scg.walk(f)
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
