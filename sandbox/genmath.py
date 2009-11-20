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

def makeName(parts):
        return "".join(parts)

def makeAltName(parts):
        return "".join([lut[part] for part in parts])

def isValidSetter(parts):
     return len(set(parts)) == len(parts)

def printGetter(name, parts):
	print "\t@property"
	print "\tdef %s(self):" % name
	if len(parts) == 1:
        	print "\t\treturn self.%s" % parts[0]
        else:
        	print "\t\treturn vec%d(%s)" % (len(parts), ", ".join(["self.%s" % part for part in parts]))

        if isValidSetter(parts):
                printSetter(name, parts)

def printSetter(name, parts):
        print "\t@%s.setter" % name
	print "\tdef %s(self, other):" % name

	# Read before write incase self and other alias
        for part, src in zip(parts, allcoords):
                print "\t\t%s = other.%s" % (src, src)
        for part, src in zip(parts, allcoords):
                print "\t\tself.%s = %s" % (part, src)


def makeSwizzle(*parts):
        name = makeName(parts)
        altName = makeAltName(parts)

        if name in allcoords:
                # Name is a real field, only generate the alternate
                printGetter(altName, parts)
                print
        else:
                printGetter(name, parts)

                print "\t%s = %s" % (altName, name)
                print

        	declGetter(name)
        	
	declGetter(altName)

def makeOpPrimitive(base, coords, forwardName, reverseName, optemplate):
	vecvec = ", ".join([optemplate % ('self.'+coord, 'other.'+coord) for coord in coords])
	vecscalar = ", ".join([optemplate % ('self.'+coord, 'other') for coord in coords])
	scalarvec = ", ".join([optemplate % ('other', 'self.'+coord) for coord in coords])

        clsName = "%s%d" % (base, len(coords))
	
	print """	def %(forwardName)s(self, other):
		if isinstance(other, %(clsName)s):
			return %(clsName)s(%(vecvec)s)
		elif isinstance(other, float):
			return %(clsName)s(%(vecscalar)s)
		else:
			return NotImplemented

	def %(reverseName)s(self, other):
		if isinstance(other, float):
			return %(clsName)s(%(scalarvec)s)
		else:
			return NotImplemented

""" % {'forwardName':forwardName, 'reverseName':reverseName, 'clsName':clsName, 'vecvec':vecvec, 'vecscalar':vecscalar, 'scalarvec':scalarvec,}

	declMethod(forwardName, (clsName, 'float'))
	declMethod(reverseName, 'float')

def makeOp(base, coords, opname, op):
        forwardName = "__%s__" % opname
        reverseName = "__r%s__" % opname
        optemplate = "%%s%s%%s" % op
        makeOpPrimitive(base, coords, forwardName, reverseName, optemplate)


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
		

def makeSubconstructor(base, count, baseType, args, indent, srcs=()):
        if len(srcs) < count:
                print "%sif isinstance(%s, %s):" % (indent, args[0], baseType)
                currentSrcs = srcs + (args[0],)
                makeSubconstructor(base, count, baseType, args[1:], indent+'\t', currentSrcs)

                for i in range(2, 5):
                        print "%selif isinstance(%s, %s%d):" % (indent, args[0], base, i)

                        currentSrcs = srcs
                        for coord in allcoords[:i]:
                                currentSrcs = currentSrcs + ("%s.%s" % (args[0], coord),)
                                if len(currentSrcs) >= count: break                                
                                
                        makeSubconstructor(base, count, baseType, args[1:], indent+'\t', currentSrcs)
                        

                if count-1 == len(args):
                        print "%selif %s is None:" % (indent, args[0])
                        makeSubconstructor(base, count, baseType, (), indent+'\t', srcs*count)
                        
                #print "%selse:\n%s\tassert False, type(%s)" % (indent, indent, args[0])
                print "%selse:\n%s\tpass #assert False, type(%s)" % (indent, indent, args[0])

        else:
                for arg in args:
                        #print "%sassert %s is None" % (indent, arg)
                        print "%spass #assert %s is None" % (indent, arg)
                
                for coord, src in zip(allcoords, srcs):
                        print "%sself.%s = %s" % (indent, coord, src)
 
def makeConstructor(base, coords):
	parts = [coords[0]]
	parts.extend(["%s=None" % coord for coord in coords[1:]])

	print "\tdef __init__(self, %s):" % ", ".join(parts)

        makeSubconstructor(base, len(coords), 'float', coords, '\t\t')
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


print >> interface, "from shader.vec import *"
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

	print "\tdef __float__(self):" 
	print "\t\treturn self.x"
	print

	declMethod('__float__')

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
	makeOp(base, coords, "pow", "**")
	makeOpPrimitive(base, coords, "min", "rmin", "min(%s, %s)")
	makeOpPrimitive(base, coords, "max", "rmax", "max(%s, %s)")

	# Swizzles
	for a in coords:
		makeSwizzle(a)
		for b in coords:
			makeSwizzle(a, b)
			for c in coords:
				makeSwizzle(a, b, c)
				for d in coords:
					makeSwizzle(a, b, c, d)
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


