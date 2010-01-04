import time
import pybind

a = pybind.vec3(1.0, 2.0, 3.0)
b = pybind.vec3(2.0, 1.0, 3.0)

def dot(a, b):
	return a.x*b.x+a.y*b.y+a.z*b.z


def dummy(a, b):
	pass

def test(f):
	start = time.clock()
	for i in range(1000000):
		f(a, b)
	return time.clock()-start



t1 = test(pybind.dot)
t2 = test(dummy)

print t1/t2
