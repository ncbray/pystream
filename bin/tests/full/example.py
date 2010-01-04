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
