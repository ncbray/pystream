from __future__ import absolute_import

from . decompiler_common import TestDecompiler

##class TestDiscardDecompile(TestDecompiler):
##	s = """
##def f(o, v, f):
##	f(o, v)
##	return o.x
##"""
##	inputs = [[Dummy(), 1, dummySet], [Dummy(), 1.0, dummySet], [Dummy(), True, dummySet], [Dummy(), 'foo', dummySet]]
##


def gatherArgs(*args, **kargs):
	return args, kargs


class TestFuncVargsDecompile(TestDecompiler):
	s = """
def fvargs(*args):
	return args
"""
	inputs = [[3, 2, 4, 7]]


class TestFuncKargsDecompile(TestDecompiler):
	s = """
def fkargs(kargs):
	def fkargsinner(**kargs):
		return kargs
	return fkargsinner(**kargs)
"""
	inputs = [[{'a':1, 'b':2, 'c':3}]]


class TestCallStdDecompile(TestDecompiler):
	s = """
def callstd(f):
	return f(1, 2, 3)
"""
	inputs = [[gatherArgs]]



class TestCallKwdDecompile(TestDecompiler):
	s = """
def callkwd(f):
	return f(1, 2, 3, foo='bar', thing='thang')
"""
	inputs = [[gatherArgs]]


class TestCallVargsDecompile(TestDecompiler):
	s = """
def callvargs(f):
	args = (1, 2, 3)
	return f(0, foo='bar', thing='thang', *args)
"""
	inputs = [[gatherArgs]]

class TestCallKargsDecompile(TestDecompiler):
	s = """
def callkargs(f):
	kargs = {'foo':'bar', 'thing':'thang'}
	return f(0, 1, help='me', **kargs)
"""
	inputs = [[gatherArgs]]


class TestCallVargsKargsDecompile(TestDecompiler):
	s = """
def callkargs(f, a, b):
	kargs = {'foo':'bar', 'thing':'thang'}
	return f(0, 1, help=a+b, *(1, 2, 3), **kargs)
"""
	inputs = [[gatherArgs, 'm', 'e']]
