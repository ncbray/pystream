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

def raiseTypeError(nodeName, typeName, fieldName, fieldSource):
	return 'raise TypeError, "Expected %s for field %s.%s, but got %%s instead." %% (%s.__class__.__name__)' \
			    % (str(typeName), nodeName, fieldName, fieldSource)

def makeScalarTypecheckStatement(name, fieldName, fieldSource, tn, optional, tabs, output):
	t  = makeTypecheck(fieldSource, tn, optional)
	r  = raiseTypeError(name, tn, fieldName, fieldSource)
	output.append('%sif %s: %s\n' % (tabs, t, r))

def makeTypecheckStatement(name, field, tn, optional, repeated, tabs, output):
	if repeated:
		makeScalarTypecheckStatement(name, field, field, '(list, tuple)', optional, tabs, output)

		if optional:
			output.append('%sif %s is not None:\n' % (tabs, field))
			tabs += '\t'

		output.append('%sfor _i in %s:\n' % (tabs, field))
		makeScalarTypecheckStatement(name, field+'[]', '_i', tn, False, tabs+'\t', output)
	else:
		makeScalarTypecheckStatement(name, field, field, tn, optional, tabs, output)


def makeInitStatements(name, fields, types, optional, repeated):
	inits = []
	for field in fields:
		if field in types:
			tn = typeName(types[field])
			makeTypecheckStatement(name, field, tn, field in optional, field in repeated, '\t', inits)
		elif field not in optional:
			inits.append('\tassert %s != None, "Field %s.%s is not optional."\n' % (field, name, field))

		inits.append('\tself.%s = %s\n' % (field, field))
	return inits

def makeInit(name, fields, types, optional, repeated):
	inits = makeInitStatements(name, fields, types, optional, repeated)
	inits.append('\tself.annotation = self.__emptyAnnotation__')

	if fields:
		fieldstr = ", ".join(fields)
		args = ", ".join(('self', fieldstr))
	else:
		args = 'self'

	code = "def __init__(%s):\n\tsuper(%s, self).__init__()\n%s" % (args, name, ''.join(inits))
	return code


def makeReplaceChildren(name, fields, types, optional, repeated):
	inits = makeInitStatements(name, fields, types, optional, repeated)

	if fields:
		fieldstr = ", ".join(fields)
		args = ", ".join(('self', fieldstr))
	else:
		args = 'self'


	body = ''.join(inits)
	if not body:
		body = '\tpass\n'

	code = "def replaceChildren(%s):\n%s" % (args, body)
	return code

def makeRepr(name, fields):
	interp = ", ".join(['%r']*len(fields))
	fields = " ".join("self.%s,"%field for field in fields)

	code = """def __repr__(self):
	return "%s(%s)" %% (%s)
""" % (name, interp, fields)

	return code


def makeAccept(name):
	code = """def accept(self, visitor, *args):
	return visitor.visit%s(self, *args)
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

def makeSetter(name, field, types, optional, repeated):
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
