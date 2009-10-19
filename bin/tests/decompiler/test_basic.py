from __future__ import absolute_import

import sys

from . decompiler_common import TestDecompiler, Dummy

import cStringIO

class BinTree(object):
	def __init__(self):
		self.left = None
		self.right = None

	def size(self):
		size = 1
		if self.left != None:
			size += self.left.size()

		if self.right != None:
			size += self.right.size()

		return size


# Regression test: DCE delt with attribute assignements incorrectly.
class TestBinTreeDecompile(TestDecompiler):
	s = """
def f(bt):
	root = bt()
	root.left = bt()
	root.left.left = bt()
	root.right = bt()

	temp = bt()
	temp.left = bt()

	return root.size()
"""
	inputs = [[BinTree]]


# May not work, as compilation may change the names...
##class TestDeleteDeompile(TestDecompiler):
##	s = """
##def f():
##	v = 'foobar'
##	a = 'v' in locals()
##	del v
##	b = 'v' in locals()
##	return a, b
##"""
##	inputs = [[]]

class TestReturnNoneDeompile(TestDecompiler):
	s = """
def f():
	return
"""
	inputs = [[]]

class TestReturnConstDeompile(TestDecompiler):
	s = """
def f():
	return 1.0
"""
	inputs = [[]]

class TestReturnFoldDeompile(TestDecompiler):
	s = """
def f():
	a = 1.0
	b =  2.0
	return a+b
"""
	inputs = [[]]



class TestFoldInplaceDeompile(TestDecompiler):	
	s = """
def f():
	a = 1.0
	b =  2.0
	b += a
	return b
"""

	inputs = [[]]


### Binary operators ###

class TestAddDeompile(TestDecompiler):
	s = """
def f(a, b):
	"Add two numbers."
	c = a+b
	return c
"""

	inputs = [[0, 0], [1, 0], [0, 1], [1, -1], [-1, 1], [1, 1], [-1, -1]]


class TestSubDeompile(TestDecompiler):
	s = """
def f(a, b):
	c = a-b
	return c
"""

	inputs = [[0, 0], [1, 0], [0, 1], [1, -1], [-1, 1], [1, 1], [-1, -1]]


class TestMulDeompile(TestDecompiler):
	s = """
def f(a, b):
	return a*b
"""

	inputs = [[0, 0], [1, 0], [0, 1], [1, -1], [-1, 1], [1, 1], [-1, -1]]


class TestDivDeompile(TestDecompiler):
	s = """
def f(a, b):
	return a/b
"""

	inputs = [[0, 1], [1, -1], [-1, 1], [1, 1], [-1, -1]]


	def testDivZero(self):
		self.assertRaises(ZeroDivisionError, self.f, 1, 0)
		self.assertRaises(ZeroDivisionError, self.df, 1, 0)


class TestFloorDivDeompile(TestDecompiler):
	s = """
def f(a, b):
	return a//b
"""

	inputs = [[0, 1], [1, -1], [-1, 1], [1, 1], [-1, -1]]


	def testDivZero(self):
		self.assertRaises(ZeroDivisionError, self.f, 1, 0)
		self.assertRaises(ZeroDivisionError, self.df, 1, 0)


class TestModDeompile(TestDecompiler):
	s = """
def f(a, b):
	return a%b
"""
	inputs = [[7, 2], [11, 3], [15, 5], [24, 5]]


class TestPowerDeompile(TestDecompiler):
	s = """
def f(a, b):
	return a**b
"""
	inputs = [[0, 0], [1, 0], [0, 1], [1, -1], [-1, 1], [1, 1], [-1, -1]]


class TestLShiftDeompile(TestDecompiler):
	s = """
def f(a, b):
	return a<<b
"""
	inputs = [[5, 0], [5, 1], [5, 2], [5, 9], [11, 11],]


class TestRShiftDeompile(TestDecompiler):
	s = """
def f(a, b):
	return a>>b
"""
	inputs = [[5, 0], [5, 1], [5, 2], [100000000, 9], [200000000, 11],]


class TestBinaryAndDeompile(TestDecompiler):
	s = """
def f(a, b):
	return a&b
"""
	inputs = [[0x0, 0x0], [0xFF, 0xFF], [0x0, 0xFF], [0xFF, 0x0], [0x55, 0x3C]]

class TestBinaryOrDeompile(TestDecompiler):
	s = """
def f(a, b):
	return a|b
"""
	inputs = [[0x0, 0x0], [0xFF, 0xFF], [0x0, 0xFF], [0xFF, 0x0], [0x55, 0x3C]]


class TestBinaryXorDeompile(TestDecompiler):
	s = """
def f(a, b):
	return a^b
"""
	inputs = [[0x0, 0x0], [0xFF, 0xFF], [0x0, 0xFF], [0xFF, 0x0], [0x55, 0x3C]]


### Inplace operators ###

class TestInplaceAddDeompile(TestDecompiler):
	s = """
def f(a, b):
	a += b
	return a
"""

	inputs = [[0, 0], [1, 0], [0, 1], [1, -1], [-1, 1], [1, 1], [-1, -1]]


class TestInplaceSubDeompile(TestDecompiler):
	s = """
def f(a, b):
	a -= b
	return a
"""

	inputs = [[0, 0], [1, 0], [0, 1], [1, -1], [-1, 1], [1, 1], [-1, -1]]


class TestInplaceMulDeompile(TestDecompiler):
	s = """
def f(a, b):
	a *= b
	return a
"""

	inputs = [[0, 0], [1, 0], [0, 1], [1, -1], [-1, 1], [1, 1], [-1, -1]]


class TestInplaceMultiMulDeompile(TestDecompiler):
	s = """
def multimul(a, b):
	a = a*b
	a = a*b
	a = a*b
	return a
"""
	inputs = [[0, 0], [2, 0], [0, 3], [2, -3], [-2, 3], [2, 3], [-2, -3]]


class TestInplaceDivDeompile(TestDecompiler):
	s = """
def f(a, b):
	a /= b
	return a
"""

	inputs = [[0, 1], [1, -1], [-1, 1], [1, 1], [-1, -1]]


	def testDivZero(self):
		self.assertRaises(ZeroDivisionError, self.f, 1, 0)
		self.assertRaises(ZeroDivisionError, self.df, 1, 0)


class TestInplaceFloorDivDeompile(TestDecompiler):
	s = """
def f(a, b):
	a //= b
	return a
"""

	inputs = [[0, 1], [1, -1], [-1, 1], [1, 1], [-1, -1]]


	def testDivZero(self):
		self.assertRaises(ZeroDivisionError, self.f, 1, 0)
		self.assertRaises(ZeroDivisionError, self.df, 1, 0)


class TestInplaceModDeompile(TestDecompiler):
	s = """
def f(a, b):
	a %= b
	return a
"""
	inputs = [[7, 2], [11, 3], [15, 5], [24, 5]]


class TestInplacePowerDeompile(TestDecompiler):
	s = """
def f(a, b):
	a **= b
	return a
"""
	inputs = [[0, 0], [1, 0], [0, 1], [1, -1], [-1, 1], [1, 1], [-1, -1]]


class TestInplaceLShiftDeompile(TestDecompiler):
	s = """
def f(a, b):
	a <<= b
	return a
"""
	inputs = [[5, 0], [5, 1], [5, 2], [5, 9], [11, 11],]


class TestInplaceRShiftDeompile(TestDecompiler):
	s = """
def f(a, b):
	a >>= b
	return a
"""
	inputs = [[5, 0], [5, 1], [5, 2], [100000000, 9], [200000000, 11],]


class TestInplaceBinaryAndDeompile(TestDecompiler):
	s = """
def f(a, b):
	a &= b
	return a
"""
	inputs = [[0x0, 0x0], [0xFF, 0xFF], [0x0, 0xFF], [0xFF, 0x0], [0x55, 0x3C]]

class TestInplaceBinaryOrDeompile(TestDecompiler):
	s = """
def f(a, b):
	a |= b
	return a
"""
	inputs = [[0x0, 0x0], [0xFF, 0xFF], [0x0, 0xFF], [0xFF, 0x0], [0x55, 0x3C]]


class TestInplaceBinaryXorDeompile(TestDecompiler):
	s = """
def f(a, b):
	a ^= b
	return a
"""
	inputs = [[0x0, 0x0], [0xFF, 0xFF], [0x0, 0xFF], [0xFF, 0x0], [0x55, 0x3C]]


### Unary operators ###
class TestUnarySubDeompile(TestDecompiler):
	s = """
def f(a):
	return -a
"""
	inputs = [[0], [1], [-1], [2]]

class TestUnaryPosDeompile(TestDecompiler):
	s = """
def f(a):
	return +a
"""

	inputs = [[0], [1], [-1], [2]]

class TestUnaryInvertDeompile(TestDecompiler):
	s = """
def f(a):
	return ~a
"""
	inputs = [[0], [1], [-1], [2]]





### Precedence testing ###

class TestPrec1Deompile(TestDecompiler):
	s = """
def f(a, b, c):
	return (a+b)*c
"""

	inputs = [[1, 2, 3], [7, 11, 5]]

class TestPrec2Deompile(TestDecompiler):
	s = """
def f(a, b, c):
	return c*(a+b)
"""
	inputs = [[1, 2, 3], [7, 11, 5]]

class TestPrec3Deompile(TestDecompiler):
	s = """
def f(a, b, c):
	return a*b*c
"""

	inputs = [[1, 2, 3], [7, 11, 5]]

class TestPrec4Deompile(TestDecompiler):
	s = """
def f(a, b, c):
	return (a**b)**c
"""

	inputs = [[2, 3, 5], [3, 5, 2]]

class TestPrec5Deompile(TestDecompiler):
	s = """
def f(a, b, c):
	return a**(b**c)
"""
	inputs = [[2, 3, 5], [3, 5, 2]]


def dummyAttr():
	s = Dummy()
	s.v = 7
	t = Dummy()
	t.v = 11
	
	o = Dummy()
	o.x = Dummy()
	o.x.y = (s, t)
	return o

class TestPrec6Deompile(TestDecompiler):
	s = """
def f(o, i):
	return o.x.y[i].v
"""
	inputs = [[dummyAttr(), 0], [dummyAttr(), 1]]




class TestCompareDeompile(TestDecompiler):
	s = """
def f(a, b):
	return a < b
"""
	inputs = [[0, 0], [1, 0], [0, 1], [1, -1], [-1, 1], [1, 1], [-1, -1]]


class TestCallDeompile(TestDecompiler):
	s = """
def f(o):
	return isinstance(o, str)
"""
	inputs = [[1], [1.0], [True], ['foo']]


class TestAttrDeompile(TestDecompiler):
	s = """
def f(o):
	return o.__class__
"""
	inputs = [[1], [1.0], [True], ['foo']]


class TestInplaceDeompile(TestDecompiler):
	s = """
def f(a, b, c):
	a *= b
	a -= c
	return a
"""
	inputs = [[1, 2, 3], [3, 2, 1]]

class TestGetSetAttr(TestDecompiler):
	s = """
def f(o, v):
	o.x = v
	o.y = o
	return o.y.y.x
"""
	inputs = [[Dummy(), 1], [Dummy(), 1.0], [Dummy(), True], [Dummy(), 'foo']]
		

class TestDeleteAttr(TestDecompiler):
	s = """
def f(o):
	o.x = 'foobar'
	a = hasattr(o, 'x')
	del o.x
	b = hasattr(o, 'x')
	
	return a, b
"""
	inputs = [[Dummy()]]


class TestGetSetGlobalDecompile(TestDecompiler):
	s = """
def f(v):
	global a, b
	a = v
	b = a
	return b
"""
	inputs = [[1], [1.0], [True], ['foo']]


class TestDelGlobalDecompile(TestDecompiler):
	s = """
def f():
	global v
	v = 'foobar'
	a = 'v' in globals()
	del v
	b = 'v' in globals()
	return a, b
"""
	inputs = [[]]

class TestPrintTargetDecompile(TestDecompiler):
	s = """
def testprinttarget(cls):
	f = cls()
	print >> f, "Hello,", "world"
	return f.getvalue()
"""
	inputs = [[cStringIO.StringIO]]

class TestPrintDecompile(TestDecompiler):
	s = """
def testprint():
	print "Hello,", "world"
"""

	def testPrinting(self):
		oldstdout = sys.stdout

		# Hijack stdout to test printing.
		try:
			sys.stdout = cStringIO.StringIO()
			self.f()
			example = sys.stdout.getvalue()

			sys.stdout = cStringIO.StringIO()
			self.df()
			test = sys.stdout.getvalue()

			sys.stdout = oldstdout

			self.assertEqual(example, test)
		finally:
			sys.stdout = oldstdout
	
	inputs = []

def dummySet(o, v):
	o.x = v

class TestDiscardDecompile(TestDecompiler):	
	s = """
def f(o, v, f):
	f(o, v)
	return o.x
"""
	inputs = [[Dummy(), 1, dummySet], [Dummy(), 1.0, dummySet], [Dummy(), True, dummySet], [Dummy(), 'foo', dummySet]]



class TestImport1Decompile(TestDecompiler):
	s = """
def import1():
	import random
	return random
"""
	inputs = [[]]

class TestImport2Decompile(TestDecompiler):
	s = """
def import2():
	from random import random as r, uniform as u
	return r
"""
	inputs = [[]]

class TestImport3Decompile(TestDecompiler):
	s = """
def import3():
	from .. import fullcompiler, test_full
	return fullcompiler
"""
	inputs = [[]]

class TestImport4Decompile(TestDecompiler):
	s = """
def import4():
	import os.path
	return os.path
"""
	inputs = [[]]
