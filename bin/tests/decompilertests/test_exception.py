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

from . decompiler_common import TestDecompiler, Dummy

class TestException(Exception):
	pass

class TestException2(Exception):
	pass


class TestCatchDecompile(TestDecompiler):
	s = """
def testcatch(ex):
	v = 0
	try:
		raise ex
	except ex:
		v = 1
	return v
"""
	inputs = [[TestException]]

class TestCatchAllDecompile(TestDecompiler):
	s = """
def testcatchall(ex, s):
	v = 0
	try:
		if s:
			raise ex
		else:
			return 7
	except:
		v += 1
	return v
"""
	inputs = [[TestException, False], [TestException, True]]

class TestCatchReraise(TestDecompiler):
	s = """
def testcatchreraise(ex, v):
	try:
		try:
			v += 1
			raise ex
		except:
			v += 1
			raise
		return v
	except:
		v += 1
	return v

"""
	inputs = [[TestException, 0], [TestException, -5]]

class TestCatchSSADecompile(TestDecompiler):
	s = """
def testcatchssa(ex):
	v = 0
	try:
		v = 2
		raise ex
	except ex:
		v += 1
	return v
"""
	inputs = [[TestException]]

class TestSwitchCatchDecompile(TestDecompiler):
	s = """
def testswitchcatch(ex, s):
	v = 0
	try:
		if s:
			raise ex
	except ex:
		v = 1
	return v
"""
	inputs = [[TestException, False], [TestException, True]]

# A simple case, as there is normal flow control exit, no switches, and no end finally.
class TestSwitchCatchAllDecompile(TestDecompiler):
	s = """
def testswitchcatchall(ex, s):
	v = 0
	try:
		if s: raise ex
	except:
		v = 1
	return v
"""
	inputs = [[TestException, False], [TestException, True]]


class TestSwitchThrowDecompile(TestDecompiler):
	s = """
def testswitchthrow(ex1, ex2, s):
	v = 0
	try:
		if s:
			raise ex1, 5
		else:
			raise ex2, 7
	except ex1, val:
		v = 2*val.args[0]
	except ex2, val:
		v = 3*val.args[0]
	return v
"""
	inputs = [[TestException, TestException2, False], [TestException, TestException2, True]]



class TestThrowGlobalDecompile(TestDecompiler):
	s = """
def testglobalthrow():
	v = 0
	try:
		raise Exception
	except Exception:
		v = 1
	return v
"""
	inputs =[[]]





class TestTryExceptReturnDecompile(TestDecompiler):
	s = """
def testexceptreturn(k):
	d = {'a':1, 'b':2, 'c':3, 'd':4}
	try:
		v = d[k]
	except KeyError:
		try:
			v = d[k]
		except KeyError:
			return None
	return v
"""
	inputs =[['a'], ['b'], ['e']]



class TestTryExceptAllElse1Decompile(TestDecompiler):
	s = """
def testexceptallelse1(s, v):
	try:
		if s:
			raise Exception
	except:
		v += 1
		v += 1
	else:
		v += 1
		v *= 2
		v *= 2

	return v
"""
	inputs =[[False, 0], [True, 0]]


class TestTryExceptAllElse2Decompile(TestDecompiler):
	s = """
def testexceptallelse2(s, v):
	try:
		if s:
			raise Exception
	except:
		v += 1
		v += 1
		return v
	else:
		v += 1
		v *= 2
		v *= 2

	return v
"""
	inputs =[[False, 0], [True, 0]]

class TestTryExceptAllElse3Decompile(TestDecompiler):
	s = """
def testexceptallelse3(s, v):
	try:
		if s:
			raise Exception
	except:
		v += 1
		v += 1
	else:
		v += 1
		v *= 2
		v *= 2
		return v

	return v
"""
	inputs =[[False, 0], [True, 0]]


class TestTryExceptAllElse4Decompile(TestDecompiler):
	s = """
def testexceptallelse4(s, v):
	try:
		if s:
			raise Exception
	except:
		v += 1
		v += 1
		return v
	else:
		v += 1
		v *= 2
		v *= 2
		return v
	return v
"""
	inputs =[[False, 0], [True, 0]]


class TestTryElse1Decompile(TestDecompiler):
	s = """
def testtryelse1():
	try:
		raise Exception
	except Exception:
		v = 1
	else:
		v = 0
	return v
"""
	inputs =[[]]

class TestTryElse2Decompile(TestDecompiler):
	s = """
def testtryelse2():
	try:
		raise Exception
	except:
		v = 1
	else:
		v = 0
	return v
"""
	inputs =[[]]

class TestTryElse3Decompile(TestDecompiler):
	s = """
def testtryelse3(s):
	try:
		if s:
			raise Exception
	except Exception:
		v = 1
	else:
		v = 0
	return v
"""
	inputs =[[False], [True]]


class TestTryElse4Decompile(TestDecompiler):
	s = """
def testtryelse4(s):
	try:
		if s:
			raise Exception
	except:
		v = 1
	else:
		v = 0
	return v
"""
	inputs =[[False], [True]]


class TestDegenerateTry(TestDecompiler):
	s = """
def testdegeneratetry(s):
	v = 0
	try:
		v += 1
		if s:
			raise Exception
	except:
		pass

	return v
"""
	inputs = [[False], [True]]

class TestSimpleFinally(TestDecompiler):
	s = """
def simplefinally(s):
	v = 0
	try:
		try:
			v += 1
			if s:
				raise Exception
		finally:
			v += 1
			if s:
				v *= 2
	except:
		pass

	return v
"""
	inputs = [[False], [True]]

class TestExceptFinally(TestDecompiler):
	s = """
def f():
	i = 0
	try:
		raise NotImplementedError
	except:
		i = 1
	finally:
		i = 2
	return i
"""
	inputs = [[]]

class TestExceptFinallyDual(TestDecompiler):
	s = """
def f():
	i = 0
	j = 0
	try:
		raise NotImplementedError
	except:
		i = 1
	finally:
		j = 2
	return i+j
"""
	inputs = [[]]


class TestExceptPassFinally(TestDecompiler):
	s = """
def tryexceptpassfinally():
	i = 0
	try:
		i = 1
	finally:
		pass
	return i
"""
	inputs = [[]]



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
