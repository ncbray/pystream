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

import math
from vec3 import vec3
from body import Body

def factorial(n):
	if n > 1:
		return n*factorial(n-1)
	else:
		return 1

def either(a, b):
	return a or b

def add(a, b):
	return a+b

def inrange(a):
	return 0.0 <= a <= 1.0

def call(a, b, c, d):
	f = add(a, b)
	g = add(c, d)
	return f*g

def negate(o):
	return -o

def negateConst():
	c = 1
	b = 0
	c = c+b
	return -c

def f():
	a = vec3(1.0, 2.0, 3.0)
	b = vec3(2.0, 1.0, 3.0)
	if a.x > b.x:
		c = a.dot(b)
	else:
		c = b.dot(a)
	return c


def defaultArgs(a=1, b=2):
	return a+b


def switch1(a):
	if a <= 0.0:
		return 0.0
	elif a >= 1.0:
		return 1.0
	else:
		return a

def switch2(a):
	if a <= 0.0:
		res = 0.0
	elif a >= 1.0:
		res = 1.0
	else:
		res = a

	return res
