from __future__ import absolute_import

from . decompiler_common import TestDecompiler, Dummy

class TestClosure1Decompile(TestDecompiler):
	s = """
def closure1():
	a = 0
	def g():
		return a
	return g(), g.func_name
"""


class TestClosure2Decompile(TestDecompiler):
	s = """
def closure2(i):
	a = i
	a += 1
	
	def g():
		return a
	return g(), g.func_name
"""
	inputs = [[-5], [3]]


class TestInlineFunc(TestDecompiler):
	s = """
def inlinefunc(a, b):
	def ilf(a, b):
		return a-b
	return ilf(a, b)*ilf(b,a), ilf.func_name
"""
	inputs = [[7, 3], [-10, 4]]
