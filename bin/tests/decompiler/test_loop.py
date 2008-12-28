from __future__ import absolute_import

from . decompiler_common import TestDecompiler, Dummy

class TestWhileDeompile(TestDecompiler):
	s = """
def f():
	a = 0
	while a < 10:
		a = a+1
	return a
"""


class TestWhileConstDeompile(TestDecompiler):
	s = """
def f():
	a = 0
	inc = 1
	while a < 10:
		a = a+inc
	return a
"""
	inputs = [[]]


class TestWhileParamDeompile(TestDecompiler):
	s = """
def f(inc):
	a = 0
	while a < 10:
		a = a+inc
	return a
"""

	inputs = [[3], [4], [5], [6], [7]]

class TestWhileIfDeompile(TestDecompiler):
	s = """
def f(inc):
	a = 0
	while a < 11:
		if a%2 == 0:
			out = 0
		else:
			out = a
		if out:
			out = out*2
			
		a = a+inc
	return out
"""

	inputs = [[1], [2], [3], [4], [5], [6], [7]]


class TestIsPrimeDecompile(TestDecompiler):	
	s = """
def f(num):
	if num <= 3: return True
	if num % 2 == 0: return False

	test = 3
	while test < num:
		if num%test == 0:
			return False
		test = test + 2
		
	return True
"""

	inputs = [[1], [2], [3], [4], [5], [6], [7], [8], [9], [10], [11]]



class TestFindPrimesDeompile(TestDecompiler):
	s = """
def findPrimes(limit):
	primes = [2]
	current = 3
	while current < limit:
		if current%3!=0:
			primes.append(current)
		current = current + 2
	return primes
"""
	inputs = [[7], [20]]

class TestLoopComprehension(TestDecompiler):
	s = """
def f(a):
	l = []
	for i in a:
		l.append(i*i)
	return l
"""

	inputs = [[[1, 2, 3]], [[-1.0, 11.0, 3.1415, -100.0]]]


class TestForReturn(TestDecompiler):
	s = """
def forreturn(limit):
	for i in range(10):
		if i > limit:
			return i
	return 0
"""

	inputs = [[-10], [0], [1], [2], [9], [10], [100]]

class TestForBreak(TestDecompiler):
	s = """
def forbreak(limit):
	for i in range(10):
		if i > limit:
			i += 10
			break
	return i
"""

	inputs = [[-20], [0], [1], [2], [9], [10], [100]]


class TestWhileBreak(TestDecompiler):
	s = """
def whilebreak(limit):
	i = 0
	while i < limit:
		i += 3
		if not i%7:
			break
	else:
		if i%2:
			i -= 1
	return i
"""
	inputs = [[-20], [-1], [0], [1], [2], [3], [7], [11], [14], [21], [42]]


class TestForBreak(TestDecompiler):
	s = """
def f(limit):
	if limit < 2:
		return 1
		
	for i in range(2, 100):
		if limit%i == 0:
			break
	return i
"""
	inputs = [[-20], [-1], [0], [1], [2], [3], [7], [11], [14], [21], [42]]

class TestWhileWhile(TestDecompiler):
	s = """
def f(limit):
	count = 0
	a = 0
	while a<limit:
		b = 0
		a += 1		
		while b<limit:
			count += 1
			b += 1
	return count
"""
	inputs = [[-20], [-10], [-1], [0], [1], [2], [10]]


class TestForDecompile(TestDecompiler):
	s = """
def fordecompile(limit):
	count = 0
	for a in range(limit):
		count += 1
	return count
"""
	inputs = [[-20], [-10], [-1], [0], [1], [2], [10]]


class TestForForDecompile(TestDecompiler):
	s = """
def forfor(limit):
	count = 0
	for a in range(limit):
		for b in range(limit):
			count += 1
	return count
"""
	inputs = [[-20], [-10], [-1], [0], [1], [2], [10]]

class TestForForBreak(TestDecompiler):
	s = """
def f(a, b, c, d):
	for i in range(a, b):
		for j in range(c, d):
			if i%j == 0:
				break
	return i, j
"""
	inputs = [[101, 103, 2, 5], [103, 105, 3, 5]]

class TestWhileCompound(TestDecompiler):
	s = """
def whilecompound(limit):
	i = 2
	while i < limit and limit%i!=0:
		i += 1
	return i
"""
	inputs = [[5], [6], [7], [8], [9], [10], [11], [12]]


# Tortures the decompiler.  Break in switch, continue in switch, and break in loop else.
class TestForElseBreak(TestDecompiler):
	s = """
def forelsebreak(a, b):
	for i in range(a, b+1):
		if i%2==0: continue
		
		for j in range(3, i, 2):
			if i%j==0: break
		else:
			break
	return i, j
"""

	inputs = [[8, 15], [99, 103], [24, 26]]

# A slight modification to the above that can cause issues with merging undefined.
class TestForElseBreak2(TestDecompiler):
	s = """
def forelsebreak2(a, b):
	i = 0
	for i in range(a, b+1):
		if i%2==0: continue

		#j = 0 # HACK?
		for j in range(3, i, 2):
			if i%j==0: break
		else:
			i *= 2
			j *= 2
			break
	return i, j
"""

	inputs = [[8, 15], [99, 103], [24, 26],
		  #[100, 99]
		  ]

# Computationally equivilent to the above, uses while loops instead of for loops.
class TestWhileElseBreak(TestDecompiler):
	s = """
def whileelsebreak(a, b):
	i = a
	while i <= b:
		if i%2==0:
			i += 1
			continue

		j = 3
		while j < i:
			if i%j==0: break
			j += 2
		else:
			break
		i += 1
	return i, j
"""

	inputs = [[8, 15], [99, 103], [24, 26]]

# A slight modification to the above that causes issues with merging undefined.
class TestWhileElseBreak2(TestDecompiler):
	s = """
def whileelsebreak2(a, b):
	i = a
	while i <= b:
		if i%2==0:
			i += 1
			continue

		j = 3
		while j < i:
			if i%j==0: break
			j += 2
		else:
			i *= 2
			j *= 2
			break
		i += 1
	return i, j
"""

	inputs = [[8, 15], [99, 103], [24, 26]]

# Note that "while True:" reads a global, so it isn't constant folded...
# "while 1:" is much uglier.
class TestInfLoop(TestDecompiler):
	s = """
def infloop(limit):
	count = 1
	while 1:
		count *= 2
		if count >= limit:
			break
	return count
"""
	inputs = [[2], [3], [4], [27], [345]]


class TestParserLoop(TestDecompiler):
	s = """
def parserloop(prgm):
	value 	= 0
	pos 	= 0
	dummy 	= 0

	shift = set(('a', 's'))
	scale = set(('d', 'h', 'n'))
	while 1:
		if prgm[pos] in shift:
			if prgm[pos] == 'a':
				value += 1
				pos += 1
			elif prgm[pos] == 's':
				value -= 1
				pos += 1
		elif prgm[pos] in scale:
			if prgm[pos] == 'd':
				value *= 2
				pos += 1
			elif prgm[pos] == 'h':
				value /= 2
				pos += 1
				continue # This is what can cause problems!
			elif prgm[pos] == 'n':
				value = -value
				pos += 1
			dummy += 1
		elif prgm[pos] == 'x':
			break
	return value, dummy
"""
	inputs = [['x'], ['ax'], ['ssx'], ['adadadx'], ['aaaddhnx']]


class TestDegenerateForDecompile(TestDecompiler):
	s = """
def degenerateFor(l):
	for i in l:
		break
	return i
"""
	inputs = [['hello world'],[range(5,10)]]


class TestDegenerateWhile1Decompile(TestDecompiler):
	s = """
def degenerateWhile1(limit, step):
	count = 0
	while count < limit:
		count += step
		break
	return count
"""
	inputs = [[100, 3],[100, 5], [-1, 2]]


class TestDegenerateWhile2Decompile(TestDecompiler):
	s = """
def degenerateWhile2(limit, step):
	count = 0
	while count < limit and step < 5:
		count += step
		break
	return count
"""
	inputs = [[100, 3],[100, 5], [-1, 2]]




class TestDoubleDegenerateWhile1Decompile(TestDecompiler):
	s = """
def doubleDegenerateWhile1(a, b):
	while 1:
		if a:
			value = 0
			break
		elif b:
			value = 1
			break
		else:
			value = 2
			break
	return value
"""
	inputs = [[False, False], [False, True], [True, False], [True, True]]


class TestDoubleDegenerateWhile2Decompile(TestDecompiler):
	s = """
def doubleDegenerateWhile2(a, b):
	while 1:
		if not a and not b:
			value = 0
			break
		elif a and not b:
			value = 1
			break
		elif not a and b:
			value = 2
			break
		else:
			value = 3
			break
	return value
"""
	inputs = [[False, False], [False, True], [True, False], [True, True]]


class TestElseContinueDecompile(TestDecompiler):
	s = """
def elseContinue(l, limit):
	while 1:
		for i in l:
			if i < limit:
				break
		else:
			limit -= 1
			continue
		break
	return limit
"""
	inputs = [[range(10), 13], [(7, 5, 8, 3), 10]]




class TestForGlobal(TestDecompiler):
	s = """
def forglobal(l, known):
	global i
	outp = []
	for i in l:
		if i not in known:
			outp.append(i)
	return outp
"""
	inputs = [[range(10), (2, 5)], [(7, 5, 8, 3), (10, 8)]]



class TestForAttr(TestDecompiler):
	s = """
def forattr(l, known, o):
	outp = []
	for o.i in l:
		if o.i not in known:
			outp.append(o.i)
	return outp
"""
	inputs = [[range(10), (2, 5), Dummy()], [(7, 5, 8, 3), (10, 8), Dummy()]]



class TestForSubscript(TestDecompiler):
	s = """
def foraub(l, known):

	temp = [0]
	
	outp = []
	for temp[0] in l:
		if temp[0] not in known:
			outp.append(temp[0])
	return outp
"""
	inputs = [[range(10), (2, 5)], [(7, 5, 8, 3), (10, 8)]]


class TestForCell(TestDecompiler):
	s = """
def forcell(l, known):
	def square():
		return i*i
	outp = []
	for i in l:
		if i not in known:
			outp.append(square())
	return outp
"""
	inputs = [[range(10), (2, 5)], [(7, 5, 8, 3), (10, 8)]]
