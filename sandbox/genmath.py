allcoords = ('x', 'y', 'z', 'w')
allcolors = ('r', 'g', 'b', 'a')


# TODO r, g, b, a properties.
# TODO flexible constructor

lut = {}

for coord, color in zip(allcoords, allcolors):
	lut[coord] = color


interface = open('interface_vec.py', 'w')

def typestr(types):
	if isinstance(types, (tuple, list)):
		return "(%s)" % (", ".join(types))
	else:
		return types

def declClass(name):
	print >> interface
	print >> interface, "cls = class_(%s)" % name


def declSlot(name, types):
	print >> interface, "cls.slot(%s, %s)"  % (repr(name), typestr(types))
	

def declMethod(name, *args):
		
	argstr = repr(name)

	rest = [typestr(arg) for arg in args]

	allargs = [argstr]
	allargs.extend(rest)

	
	print >> interface, "cls.method(%s)"  % (", ".join(allargs))

def declGetter(name):	
	print >> interface, "cls.getter(%s)"  % repr(name)

def make1(a):
	print "\t@property"
	print "\tdef %s(self):" % (lut[a],)
	print "\t\treturn self.%s" % (a,)
	
	declGetter(lut[a])

def make2(a, b):
	print "\t@property"
	print "\tdef %s%s(self):" % (a, b)
	print "\t\treturn vec2(self.%s, self.%s)" % (a, b)

	print "\t@property"
	print "\tdef %s%s(self):" % (lut[a], lut[b])
	print "\t\treturn vec2(self.%s, self.%s)" % (a, b)

	declGetter("%s%s"  % (a, b))	
	declGetter("%s%s"  % (lut[a], lut[b]))

def make3(a, b, c):
	print "\t@property"
	print "\tdef %s%s%s(self):" % (a, b, c)
	print "\t\treturn vec3(self.%s, self.%s, self.%s)" % (a, b, c)

	print "\t@property"
	print "\tdef %s%s%s(self):" % (lut[a], lut[b], lut[c])
	print "\t\treturn vec3(self.%s, self.%s, self.%s)" % (a, b, c)


	declGetter("%s%s%s"  % (a, b, c))	
	declGetter("%s%s%s"  % (lut[a], lut[b], lut[c]))


def make4(a, b, c, d):
	print "\t@property"
	print "\tdef %s%s%s%s(self):" % (a, b, c, d)
	print "\t\treturn vec4(self.%s, self.%s, self.%s, self.%s)" % (a, b, c, d)

	print "\t@property"
	print "\tdef %s%s%s%s(self):" % (lut[a], lut[b], lut[c], lut[d])
	print "\t\treturn vec4(self.%s, self.%s, self.%s, self.%s)" % (a, b, c, d)


	declGetter("%s%s%s%s"  % (a, b, c, d))	
	declGetter("%s%s%s%s"  % (lut[a], lut[b], lut[c], lut[d]))

def makeOp(base, coords, opname, op):
	vecvec = ", ".join(["self.%s%sother.%s" % (coord, op, coord) for coord in coords])
	vecscalar = ", ".join(["self.%s%sother" % (coord, op) for coord in coords])
	scalarvec = ", ".join(["other%sself.%s" % (op, coord) for coord in coords])
	
	print """	def __%(opname)s__(self, other):
		if isinstance(other, %(base)s%(len)s):
			return %(base)s%(len)s(%(vecvec)s)
		elif isinstance(other, float):
			return %(base)s%(len)s(%(vecscalar)s)
		else:
			return NotImplemented

	def __r%(opname)s__(self, other):
		if isinstance(other, float):
			return %(base)s%(len)s(%(scalarvec)s)
		else:
			return NotImplemented

""" % {'opname':opname, 'op':op, 'base':base, 'len':len(coords), 'vecvec':vecvec, 'vecscalar':vecscalar, 'scalarvec':scalarvec,}

	declMethod('__%s__' % opname, ('%s%d' % (base, len(coords)), 'float'))
	declMethod('__r%s__' % opname, 'float')

def makePos(base, coords):
	args = ", ".join(["+self.%s" % coord for coord in coords])
	
	print """	def __pos__(self):
		return %(base)s%(len)s(%(args)s)

""" % {'base':base, 'len':len(coords), 'args':args}
	
	declMethod('__pos__')

def makeNeg(base, coords):
	args = ", ".join(["-self.%s" % coord for coord in coords])
	
	print """	def __neg__(self):
		return %(base)s%(len)s(%(args)s)

""" % {'base':base, 'len':len(coords), 'args':args}
	
	declMethod('__neg__')

def makeAbs(base, coords):
	args = ", ".join(["abs(self.%s)" % coord for coord in coords])
	
	print """	def __abs__(self):
		return %(base)s%(len)s(%(args)s)

""" % {'base':base, 'len':len(coords), 'args':args}
	
	declMethod('__abs__')
	
def typeName(base, l):
	if l < 1 or l > 4:
		assert False
	elif l == 1:
		return 'float'
	else:
		return "%s%d" % (base, l)
		

def makeConstructor(base, coords):
	parts = [coords[0]]
	parts.extend(["%s=None" % coord for coord in coords[1:]])

	print "\tdef __init__(self, %s):" % ", ".join(parts)

##	total = 0
##	for a in len(coords):
##		total = a
##		print "\t\tif isinstance(x, %s)":
##
##		remaining = 
##		
##		if total < len(coords):
##			for b in len(coords):
##				total = a+b
##				if total < len(coords):
##					for c in len(coords):
##						total = a+b+c
##						if total < len(coords):
##							for d in len(coords):
##								total = a+b+c+d
##									if total < len(coords):
##										pass
##
	for coord in coords:
		print "\t\tself.%s = %s" % (coord, coord)
	print

	args = ['float']*len(coords)
	declMethod('__init__', *args)


def matrixMul(mbase, vbase, l):
	print "\tdef __mul__(self, other):"
	print "\t\tif isinstance(other, %s%d):" % (vbase, l)
	args = ", ".join(["+".join(["self.m%d%d*other.%s" % (a, b, allcoords[b])for b in range(l)]) for a in range(l)])
	print "\t\t\treturn %s%d(%s)" % (vbase, l, args)
	
	print "\t\telif isinstance(other, %s%d):" % (mbase, l)
	args = ", ".join(["+".join(["self.m%d%d*other.m%d%d" % (b, c, c, a) for c in range(l)]) for b in range(l) for a in range(l)])
	print "\t\t\treturn %s%d(%s)" % (mbase, l, args)

	print "\t\telif isinstance(other, float):"
	args = ", ".join(["self.m%d%d*other" % (b, a) for b in range(l) for a in range(l)])
	print "\t\t\treturn %s%d(%s)" % (mbase, l, args)
	print "\t\telse:"
	print "\t\t\treturn NotImplemented"
	print

	declMethod('__mul__', ('%s%d'% (vbase, l), '%s%d'% (mbase, l), 'float'))

	print "\tdef __imul__(self, other):"
	print "\t\tif isinstance(other, %s%d):" % (vbase, l)
	args = ", ".join(["+".join(["self.m%d%d*other.%s" % (b, a, allcoords[b])for b in range(l)]) for a in range(l)])
	print "\t\t\treturn %s%d(%s)" % (vbase, l, args)
	
	print "\t\telif isinstance(other, float):"
	args = ", ".join(["self.m%d%d*other" % (b, a) for b in range(l) for a in range(l)])
	print "\t\t\treturn %s%d(%s)" % (mbase, l, args)
	print "\t\telse:"
	print "\t\t\treturn NotImplemented"
	print

	declMethod('__imul__', ('%s%d'% (vbase, l), 'float'))


print >> interface, "from vec import *"
print >> interface, "from decl import *"

### Declare vectors

for l in range(2, 5):
	coords = allcoords[:l]
	base = "vec"
	
	print "class %s%d(object):" % (base, l)
	print "\t__slots__ = %s" % (", ".join([repr(coord) for coord in coords]))
	print

	declClass("%s%d" % (base, l))
	for coord in coords:
		declSlot(coord, 'float')

	makeConstructor(base, coords)
	

	print "\tdef __repr__(self):" 
	print "\t\treturn \"%s%d(%s)\" %% (%s,)" % (base, len(coords), ", ".join(["%s"]*len(coords)), ", ".join(["self.%s" % coord for coord in coords]))
	print

	declMethod('__repr__')

	print """	def dot(self, other):
		#assert type(self) is type(other)
		return %s

""" % ("+".join(["self.%s*other.%s" % (coord, coord) for coord in coords]),)


	declMethod('dot', "%s%d" % (base, l))

	print """	def length(self):
		return self.dot(self)**0.5

"""

	declMethod('length')


	print """	def normalize(self):
		return self/self.length()

"""

	declMethod('normalize')


	if l == 3:
		print """	def cross(self, other):
		x = self.y*other.z-self.z*other.y
		y = self.z*other.x-self.x*other.z
		z = self.x*other.y-self.y*other.x
		return vec3(x, y, z)

"""
		declMethod('cross', "%s%d" % (base, l))

	makePos(base, coords)
	makeNeg(base, coords)
	makeAbs(base, coords)

	makeOp(base, coords, "add", "+")
	makeOp(base, coords, "sub", "-")
	makeOp(base, coords, "mul", "*")
	makeOp(base, coords, "div", "/")

	# Swizzles
	for a in coords:
		make1(a)
		for b in coords:
			make2(a, b)
			for c in coords:
				make3(a, b, c)
				for d in coords:
					make4(a, b, c, d)
	print


# Matrix
for l in range(2, 5):
	coords = allcoords[:l]
	mcoords = ["m%d%d" % (a, b) for a in range(l) for b in range(l)]
	base = "mat"
	
	print "class %s%d(object):" % (base, l)
	print "\t__slots__ = %s" % (", ".join("'%s'" % mc for mc in mcoords))
	print

	declClass("%s%d" % (base, l))

	for coord in mcoords:
		declSlot(coord, 'float')


	print "\tdef __init__(self, %s):" % ", ".join(mcoords)
	for mc in mcoords:
		print "\t\tself.%s = %s" % (mc, mc)
	print

	declMethod('__init__', *(['float']*len(mcoords)))

	print "\tdef __repr__(self):" 
	print "\t\treturn \"%s%d(%s)\" %% (%s,)" % (base, l, ", ".join(["%s"]*len(mcoords)), ", ".join(["self.%s" % coord for coord in mcoords]))
	print

	declMethod('__repr__')

	matrixMul(base, 'vec', l)


