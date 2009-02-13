def compileFunc(s, g=None):
	l = {}
	eval(compile(s, '<string>', 'exec'), g, l)
	assert len(l) == 1
	return l.values()[0]


def typeName(types):
	if isinstance(types, str):
		return types
	elif isinstance(types, (tuple, list)):
		return "(%s)" % ''.join(["%s,"%typeName(t) for t in types])
	elif isinstance(types, type):
		return types.__name__


def makeTypecheck(target, tn, optional):
	# The exception for "Symbol" allows all AST nodes to be used for pattern matching.
	t = "not isinstance(%s, %s) and not isinstance(%s, Symbol)" % (target, tn, target)
	if optional:
		t = "%s != None and %s" % (target, t)
	return t

def makeInit(name, fields, types, optional):
	args = ", ".join(('self', ", ".join(fields)))

	inits = []
	for field in fields:
		if field in types:
			tn = typeName(types[field])
			t = makeTypecheck(field, tn, field in optional)
			# TODO simplify: interpolating constant strings
			r = 'raise TypeError, "Expected %%s for field %s.%%s, got %%s" %% (%r, %r, type(%s).__name__)' \
			    % (name, tn, field, field)
			inits.append('\tif %s: %s\n' % (t, r))
		elif field not in optional:
			inits.append('\tassert %s != None, "Field %s.%s is not optional."\n' % (field, name, field))

		inits.append('\tself.%s = %s\n' % (field, field))

	inits.append('\tself.annotation = self.emptyAnnotation')

	code = "def __init__(%s):\n\tsuper(%s, self).__init__()\n%s" % (args, name, ''.join(inits))
	return code

def makeRepr(name, fields):
	interp = ", ".join(['%r']*len(fields))
	fields = " ".join("self.%s,"%field for field in fields)

	code = """def __repr__(self):
	return "%s(%s)" %% (%s)
""" % (name, interp, fields)

	return code


def makeAccept(name):
	code = """def accept(self, visitor, *args, **kargs):
	return visitor.visit%s(self, *args, **kargs)
""" % (name)

	return code

def makeGetChildren(fields):
	children = ' '.join(["self.%s," % field for field in fields])
	code = """def children(self):
	return (%s)
""" % (children)

	return code


def makeGetFields(fields):
	children = ' '.join(["(%r, self.%s)," % (field, field) for field in fields])
	code = """def fields(self):
	return (%s)
""" % (children)

	return code


def makeHash(fields):
	children = ' '.join(["self.%s," % field for field in fields])
	code = """def asthash(self):
	return id(type(self))^hash((%s))
""" % (children)

	return code

def makeEq(fields):
	if fields:
		children = ' and '.join(["asteq(self.%s, other.%s)" % (field, field) for field in fields])
		code = """def asteq(self, other):
	return type(self) is type(other) and %s
""" % (children)
	else:
		code = """def __eq__(self, other):
	return type(self) is type(other)
"""
	return code

def makeSetter(name, field, types, optional):
	inits = []

	if types:
		tn = typeName(types)
		t = makeTypecheck('value', tn, optional)
		#r = 'raise TypeError, "Expected %%s for field %s.%%s, got %%s" %% (%s, %s, type(%s).__name__)' % (name, repr(tn), repr(field), field)
		inits.append('\tassert not(%s), (type(self), %r, value)\n' % (t, field))
	elif not optional:
		inits.append('\tassert value != None, "Field %s.%s is not optional."\n' % (name, field))

	inits.append('\tself._%s = value\n' % (field))


	code = "def __set_%s__(self, value):\n%s" % (field, ''.join(inits))

	return code

def makeGetter(name, field):
	code = "def __get_%s__(self):\n\treturn self._%s\n" % (field, field)
	return code
