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

from vec3 import vec3

def doDot():
	v0 = vec3(1.0, 2.0, 3.0)
	v1 = vec3(2.0, 1.0, 3.0)
	return v0.dot(v1)

def doDotHalf(a, b, c):
	v0 = vec3(a, b, c)
	v1 = vec3(2.0, 1.0, 3.0)
	return v0.dot(v1)

def doDotFull(a, b, c, d, e, f):
	v0 = vec3(a, b, c)
	v1 = vec3(d, e, f)
	return v0.dot(v1)


def doStaticSwitch():
	s = 1
	if s:
		a = 3
		b = 2
	else:
		a = 1
		b = 1
	return a+b



def doDynamicSwitch(s):
	if s:
		a = 3
		b = 2
	else:
		a = 1
		b = 1
	return a+b

def doSwitchReturn(s):
	if s:
		return True
	else:
		a = False
	return a


def doMultiSwitch(s, t):
	v = 1
	if s: v = v*3
	if t: v = v*7
	return v

def doOr(cond, t, f):
	if cond:
		return t
	else:
		return f

# Generates divergent preconditions.
def twisted(a):
	if a<10:
		return 10
	else:
		return a-10


##def reallyTwisted(a):
##	if a<10:
##		v = 10
##	else:
##		if a >= 0:
##			v = 0 # HACK?
##			return a
##		else:
##			v = a-10
##	return v

class BinTree(object):
	__slots__ = 'left', 'right'

	def __init__(self):
		self.left = None
		self.right = None


def testBinTree():
	root = BinTree()
	root.left = BinTree()
	# Causes problems if not flow sensitive
	# as root.left may be None...
	root.left.left = BinTree()
	root.right = BinTree()

	temp = BinTree()
	temp.left = BinTree()

	return root


def testAttrMerge(s):
	v = vec3(0.0, 0.0, 0.0)
	if s: v.x = 1.0
	return v.x


def vecSwitch(s):
	if s:
		return vec3(11.0, 11.0, 11.0)
	else:
		return vec3(7.0, 7.0, 7.0)

def dummy(s):
	return vecSwitch(s)

def testCall(s):
	res = dummy(s)
	return res.x


# Tests the resolution of opaque pointers.
def attrMunge(s2, v, a, b):
	if s2:
		v.x = a.x
	else:
		v.x = b.x

def vecAttrSwitch(s):
	a = vec3(11.0, 11.0, 11.0)
	b = vec3(7.0, 7.0, 7.0)
	v = vec3(0.0, 0.0, 0.0)
	attrMunge(s, v, a, b)
	return v


def selfCorrelation(s):
	if s:
		i = 3
	else:
		i = 5

	# Should return 6 or 10
	# Without self correlation, returns 6, 8(x2), and 10
	return i+i

def groupCorrelation(s):
	i = selfCorrelation(s)
	j = i-2

	# Should return 24 and 80
	# With self but without group correlation, returns 24, 40, 48 and 80
	# Without either, returns 24, 36(x4), 48(x6), 60(x2), 64(x2), 80
	# Without correlation, grows as ~O(ntypes^nargs)
	return i*j




class VecSetter(object):
	__slots__ = 'value'
	def __init__(self, value):
		self.value = value

	def setter(self, v):
		v.x = self.value
		v.y = self.value
		v.z = self.value

##class VecSetter3(object):
##	__slots__ = ()
##	def __init__(self):
##		pass
##
##	def setter(self, v):
##		v.x = 3.0
##		v.y = 3.0
##		v.z = 3.0
##
##class VecSetter5(object):
##	__slots__ = ()
##	def __init__(self):
##		pass
##
##	def setter(self, v):
##		v.x = 5.0
##		v.y = 5.0
##		v.z = 5.0


def methodMerge(s):
	v = vec3(0.0, 0.0, 0.0)
	if s:
		vs = VecSetter(5.0)
	else:
		vs = VecSetter(3.0)

##	# Old analysis method chokes, as the types are unrelated.
##	if s:
##		vs = VecSetter5()
##	else:
##		vs = VecSetter3()

	vs.setter(v)

	return v.x



def assignMerge(s):
	a = vec3(3.0, 3.0, 3.0)
	b = vec3(5.0, 5.0, 5.0)

	#c = a if s else b
	if s:
		c = a
	else:
		c = b

	c.x = 7.0

	return c.x
