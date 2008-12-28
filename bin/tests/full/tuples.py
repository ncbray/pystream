def pack(a, b, c):
	return a, b, c

def nothing(o):
	return o

def tupleTest(a, b, c):
	t = pack(a, b, c) # pack
	t = nothing(t) # tuple as argument, return value
	d, e, f = t # unpack
	return d+e-f


def constTuple():
	return (1, 2, 3)

def addConstTuple():
	a, b, c = constTuple()
	return a+b+c


def hybridTuple(x):
	return (1, 2, x)

def addHybridTuple(x):
	a, b, c = hybridTuple(x)
	return a+b+c

def makeConstCompound():
	return (((1, 2), (3, 4)), ((5, 6), (7, 8)))

def unpackConstCompound():
	((a, b), (c, d)), ((e, f), (g, h)) = makeConstCompound()
	return a*1+b*2+c*3+d*4+e*5+f*6+g*7+h*8

def makeCompound(a, b, c, d):
	return ((a, b, 1), (c, d, -1))

def unpackCompound(a, b, c, d):
	(e, f, g), (h, i, j) = makeCompound(a, b, c, d)
	return e*1+f*2+g*3+h*4+i*5+j*6

def swap(a, b):
	f = a, b
	b, a = f
	return a, b


def index():
	return (1, 2, 3)[1]

def indexNoFold():
	return nothing((1, 2, 3))[1]

def indexInt(i):
	return (1, 2, 3)[i]

