from __future__ import absolute_import

from . decompiler_common import TestDecompiler, Dummy

class TestTupleDeompile(TestDecompiler):
	s = """
def f(a, b, c):
	return c, b, a
"""
	inputs = [[1, 2, 3], [True, False, False]]

class TestSwapDeompile(TestDecompiler):
	s = """
def f(a, b, c):
	t = (a, b, c)
	d, e, f = t
	return d+e-f
"""
	inputs = [[1, 2, 3], [2, 3, 1], [3, 1, 2]]

class TestListMutate1Deompile(TestDecompiler):
	s = """
def f():
	l = [-3, -2, -1]
	l[0] = 3
	l[1] = 4
	l[2] = 5
	return l[2], l[1], l[0]
"""
	inputs = [[]]

class TestListMutate2Deompile(TestDecompiler):
	s = """
def f(a, b, c):
	temp = (b+b)
	l = [-(c+b), -temp, -(b+c)]
	l[a+a] = b+c
	l[a+b] = b+b
	l[b+b] = c+c+b
	return l[2], l[1], l[0]
"""
	inputs = [[0, 1, 2]]

class TestSubscriptMungeDeompile(TestDecompiler):
	s = """
def f(a, b, c):
	temp = ((0, 1), (2, 3))
	return temp[a+b][a+a]
"""
	inputs = [[0, 1, 2]]

class TestDictDecompile(TestDecompiler):
	s = """
def f(s):
	d = {'a':1, 'b':2, 'c':3, 'd':4}
	return d[s]
"""
	inputs = [['a'],['b'],['c'],['d']]

class TestDeleteSubscriptDecompile(TestDecompiler):
	s = """
def f(s):
	d = {'a':1, 'b':2, 'c':3, 'd':4}
	a = s in d
	del d[s]
	b = s in d
	return a, b
"""
	inputs = [['a'],['b'],['c'],['d']]	

class TestDictFlip(TestDecompiler):
	s = """
def f(d):
	nd = {}
	for key, value in d.iteritems():
		nd[value] = key
	return nd
"""
	inputs = [[{'a':'1', 'b':'2', 'c':'3', 'd':'4'}]]	

class TestGetSlice_3_1_Decompile(TestDecompiler):
	s = """
def f(a, b, c):
	l = range(20)
	return l[a:b:c]
"""
	inputs = [[0, 20, 2], [1, 20, 2]]

class TestGetSlice_3_2_Decompile(TestDecompiler):
	s = """
def f(a, c):
	l = range(20)
	return l[a::c]
"""
	inputs = [[0, 2], [1, 2]]

class TestGetSlice_2_1_Decompile(TestDecompiler):
	s = """
def f(a, c):
	l = range(20)
	return l[a:c]
"""
	inputs = [[3, 11], [7, 13]]

class TestGetSlice_1_1_Decompile(TestDecompiler):
	s = """
def f(a):
	l = range(20)
	return l[a:]
"""
	inputs = [[3], [13]]

class TestGetSlice_1_2_Decompile(TestDecompiler):
	s = """
def f(a):
	l = range(20)
	return l[:a]
"""
	inputs = [[3], [13]]

class TestGetSlice_0_1_Decompile(TestDecompiler):
	s = """
def f():
	l = range(20)
	return l[:]
"""
	inputs = [[]]


class TestSetSlice_3_1_Decompile(TestDecompiler):
	s = """
def f():
	l = range(20)
	l[1:20:2] = range(10)
	return l
"""
	inputs = [[]]

class TestSetSlice_2_1_Decompile(TestDecompiler):
	s = """
def f():
	l = range(20)
	l[1:5] = range(10)
	return l
"""
	inputs = [[]]

class TestSetSlice_2_2_Decompile(TestDecompiler):
	s = """
def f():
	l = range(20)
	l[3:] = range(10)
	return l
"""
	inputs = [[]]

class TestSetSlice_2_3_Decompile(TestDecompiler):
	s = """
def f():
	l = range(20)
	l[:15] = range(10)
	return l
"""
	inputs = [[]]

class TestSetSlice_1_1_Decompile(TestDecompiler):
	s = """
def f():
	l = range(20)
	l[:] = range(10)
	return l
"""
	inputs = [[]]

class TestDeleteSlice_3_1(TestDecompiler):
	s = """
def f(a, b, c):
	l = range(20)
	del l[a:b:c]
	return l
"""
	inputs = [[1, 10, 2], [5, 19, 3]]
	

class TestDeleteSlice_2_1(TestDecompiler):
	s = """
def f(a, b):
	l = range(20)
	del l[a:b]
	return l
"""
	inputs = [[1, 10], [5, 15]]

class TestDeleteSlice_1_1(TestDecompiler):
	s = """
def f(a):
	l = range(20)
	del l[a:]
	return l
"""
	inputs = [[3], [15]]

class TestDeleteSlice_1_2(TestDecompiler):
	s = """
def f(a):
	l = range(20)
	del l[:a]
	return l
"""
	inputs = [[3], [15]]


class TestDeleteSlice_0_1(TestDecompiler):
	s = """
def f():
	l = range(20)
	del l[:]
	return l
"""
	inputs = []

# Note: the LIST_APPEND will be on a seperate line, even when collapsed, due to order of operations.
class TestListComprehension(TestDecompiler):
	s = """
def listcomp(a):
	l = [i*i for i in a]
	return l
"""
	inputs =[[[3, 7, 5]], [[11, -3, 2]]]

def makeMod1():
	d = Dummy()
	d.__all__ = ('a', 'b', 'c')
	d.x = 4
	return d

def makeMod2():
	d = Dummy()
	d.w = 3
	d.x = 4
	d.y = 5
	d.z = 6
	return d


class TestComplexListComprehension(TestDecompiler):
	s = """
def complexlistcomp(module):
    try:
        return list(module.__all__)
    except AttributeError:
        return [n for n in dir(module) if n[0] != '_']
"""
	inputs = [[makeMod1()], [makeMod2()]]

# Note: tuple comprehensions create generators.
class TestTupleComprehension(TestDecompiler):
	s = """
def tuplecomp(a):
	l = (i*i for i in a)
	return list(l)
"""
	inputs =[[(3, 7, 5)], [(11, -3, 2)]]

# Tuple comprehension?
