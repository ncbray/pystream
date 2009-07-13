from math import *

def numbits(size):
	if size <= 1:
		return 0
	else:
		return int(ceil(log(size, 2)))

def _bijection(a, b):
	c = a+b
	return (c*(c+1))//2+a

def bijection(a, b, *others):
	result = _bijection(a, b)
	for o in others:
		result = _bijection(result, o)
	return result