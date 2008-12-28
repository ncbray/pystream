from __future__ import absolute_import

from . decompiler_common import TestDecompiler

from . import config


if not config.skipKnownProblems:
	class TestCompareChainDeompile(TestDecompiler):
		s = """
	def f(a, b, c):
		return a < b < c
	"""
		inputs = [[0, 0, 1], [1, 0, 1], [0, 1, 2], [1, -1, 0], [-1, 1, 2], [1, 1, 0], [-1, -1, 1]]



if not config.skipKnownProblems:
	class TestCompareConstChainDeompile(TestDecompiler):	
		s = """
	def f(a):		
		return 0.0 < a < 2.0
	"""
		inputs = [[0], [1], [-1], [2]]


if not config.skipKnownProblems:
	class TestDirectOrDeompile(TestDecompiler):
		trace = True
		s = """
	def directOr(a, b, c):		
		return a or b or c
	"""
		inputs = [[0, 0, 0], [1, 0, 0], [0, 2, 0], [0, 0, 3], [1, 0, 3], [0, 2, 3], [1, 2, 0], [1, 2, 3]]


if not config.skipKnownProblems:
	class TestDirectOrCompareDecompile(TestDecompiler):
		#trace= True
		s = """
	def directorcompare(c):
	    return 'a'<=c<='z' or 'A'<=c<='Z' or c == '_'
	"""
		inputs = [['f'], ['6'], ['_'], ['#']]

class TestNotDecompile(TestDecompiler):
	s = """
def testnot(a):
	return not a
"""
	inputs =[[False], [True], [0], [1]]

	
class TestOrDecompile(TestDecompiler):
	s = """
def testor(a, b):
	v = 0
	if a or b:
		v += 1
	return v
"""
	inputs =[[False, False], [True, False], [False, True], [True, True]]


class TestAndDecompile(TestDecompiler):
	s = """
def testand(a, b):
	v = 0
	if a and b:
		v += 1
	return v
"""
	inputs =[[False, False], [True, False], [False, True], [True, True]]


class TestXorDecompile(TestDecompiler):
	s = """
def testxor(a, b):
	v = 0
	if a and not b or not a and b:
		v += 1
	return v
"""
	inputs =[[False, False], [True, False], [False, True], [True, True]]

class TestMajority1Decompile(TestDecompiler):
	s = """
def testmajority31(a, b, c):
	v = 0
	if (a or b) and (b or c) and (c or a):
		v += 1
	return v
"""
	inputs =[
		[False, False, False], [False, True, False],
		[False, False, True], [False, True, True],
		[True, False, False], [True, True, False],
		[True, False, True], [True, True, True],
		]

class TestMajority2Decompile(TestDecompiler):
	s = """
def testmajority32(a, b, c):
	v = 0
	if (a and b) or (b and c) or (c and a):
		v += 1
	return v
"""
	inputs =[
		[False, False, False], [False, True, False],
		[False, False, True], [False, True, True],
		[True, False, False], [True, True, False],
		[True, False, True], [True, True, True],
		]

# AN ugly case.
	
##class TestCompareChainCondition(TestDecompiler):
##	trace = True
##
##	s = """
##def testchaincondition(a, b, c, d):
##	v = 0
##	if a <= b <= c <= d:
##		v += 1
##	return v
##"""
##	inputs = [
##		[0, 1, 2, 3], [0, 2, 1, 3], [1, 0, 2, 3], [1, 2, 0, 3], [2, 0, 1, 3], [2, 1, 0, 3],
##		[0, 1, 3, 2], [0, 2, 3, 1], [1, 0, 3, 2], [1, 2, 3, 0], [2, 0, 3, 1], [2, 1, 3, 0],
##		[0, 3, 1, 2], [0, 3, 2, 1], [1, 3, 0, 2], [1, 3, 2, 0], [2, 3, 0, 1], [2, 3, 1, 0],
##		[3, 0, 1, 2], [3, 0, 2, 1], [3, 1, 0, 2], [3, 1, 2, 0], [3, 2, 0, 1], [3, 2, 1, 0],
##		]

class TestCompareAndCondition(TestDecompiler):
	s = """
def testandcondition(a, b, c, d):
	v = 0
	if a <= b and b <= c and c <= d:
		v += 1
	return v
"""
	inputs = [
		[0, 1, 2, 3], [0, 2, 1, 3], [1, 0, 2, 3], [1, 2, 0, 3], [2, 0, 1, 3], [2, 1, 0, 3],
		[0, 1, 3, 2], [0, 2, 3, 1], [1, 0, 3, 2], [1, 2, 3, 0], [2, 0, 3, 1], [2, 1, 3, 0],
		[0, 3, 1, 2], [0, 3, 2, 1], [1, 3, 0, 2], [1, 3, 2, 0], [2, 3, 0, 1], [2, 3, 1, 0],
		[3, 0, 1, 2], [3, 0, 2, 1], [3, 1, 0, 2], [3, 1, 2, 0], [3, 2, 0, 1], [3, 2, 1, 0],
		]
