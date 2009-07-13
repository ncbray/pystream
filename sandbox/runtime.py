from __future__ import absolute_import

from streamRT import *

@kernel
def f(a, b):
	return a+b

def testF():
	a = stream()
	a.push(1)
	a.push(2)

	b = stream()
	b.push(7)
	b.push(5)

	c = f(a, b)

	return c[0]+c[1]
