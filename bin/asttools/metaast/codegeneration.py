def compileFunc(clsname, s, g=None):
	l = {}
	eval(compile(s, '<metaast - %s>' % clsname, 'exec'), g, l)
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
	t = "not isinstance(%s, %s)" % (target, tn)
	if optional:
		t = "%s is not None and %s" % (target, t)
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


def makeInitStatements(clsname, paramnames, fields, types, optional, repeated, dopostinit):
	inits = []
	for name, field in zip(paramnames, fields):
		if name in types:
			tn = typeName(types[name])
			makeTypecheckStatement(clsname, name, tn, name in optional, name in repeated, '\t', inits)
		elif name not in optional:
			inits.append('\tassert %s is not None, "Field %s.%s is not optional."\n' % (name, clsname, name))

		inits.append('\tself.%s = %s\n' % (field, name))

	if dopostinit:
		inits.append('\tself.__postinit__()\n')

	return inits

def argsFromParamNames(paramnames):
	if paramnames:
		fieldstr = ", ".join(paramnames)
		args = ", ".join(('self', fieldstr))
	else:
		args = 'self'
	return args

def makeBody(code):
	if not code:
		return '\tpass\n'
	else:
		return code

def makeInit(name, paramnames, fields, types, optional, repeated, dopostinit):
	inits = makeInitStatements(name, paramnames, fields, types, optional, repeated, dopostinit)
	inits.append('\tself.annotation = self.__emptyAnnotation__')

	args = argsFromParamNames(paramnames)

	# NOTE super.__init__ should be a no-op, as we're initializing all the fields, anyways?
	#code = "def __init__(%s):\n\tsuper(%s, self).__init__()\n%s" % (args, name, ''.join(inits))
	code = "def __init__(%s):\n%s" % (args, ''.join(inits))
	return code


def makeReplaceChildren(name, paramnames, fields, types, optional, repeated, dopostinit):
	inits = makeInitStatements(name, paramnames, fields, types, optional, repeated, dopostinit)

	args = argsFromParamNames(paramnames)

	body = makeBody(''.join(inits))

	code = "def _replaceChildren(%s):\n%s" % (args, body)
	return code

def makeRepr(name, fields):
	interp = ", ".join(['%r']*len(fields))
	fields = " ".join("self.%s,"%field for field in fields)

	code = """def __repr__(self):
	return "%s(%s)" %% (%s)
""" % (name, interp, fields)

	return code

# To prevent possible recursion, shared node do NOT print their children.
def makeSharedRepr(name, fields):
	code = """def __repr__(self):
	return "%s(%%d)" %% (id(self),)
""" % (name)

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


def makeGetFields(paramnames, fields):
	children = ' '.join(["(%r, self.%s)," % (name, field) for name, field in zip(paramnames, fields)])
	code = """def fields(self):
	return (%s)
""" % (children)

	return code

def makeSetter(clsname, field, slot, types, optional, repeated):
	inits = []

	tn = typeName(types)
	makeTypecheckStatement(clsname, field, tn, optional, repeated, '\t', inits)
	inits.append('\tself.%s = %s\n' % (slot, field))

	code = "def __set_%s__(self, %s):\n%s" % (field, field, ''.join(inits))
	return code

def makeGetter(clsname, field, slot):
	code = "def __get_%s__(self):\n\treturn self.%s\n" % (field, slot)
	return code


def makeVisit(clsname, desc, reverse=False, shared=False, forced=False, vargs=False, kargs=False):
	args = "self, _callback"

	additionalargs = ''
	if vargs:
		additionalargs += ', *vargs'
	if kargs:
		additionalargs += ', **kargs'
	args += additionalargs

	statements = []
	
	if not shared or forced:
		iterator = reversed(desc) if reverse else desc
		
		for field in iterator:
			indent = '\t'
			
			if field.optional:
				statements.append('%sif self.%s is not None:\n' % (indent, field.internalname))
				indent += '\t'
	
			if field.repeated:
				statements.append('%sfor _child in self.%s:\n' % (indent, field.internalname))
				indent += '\t'
				src = '_child'
			else:
				src = 'self.' + field.internalname
	
			statements.append('%s_callback(%s%s)\n' % (indent, src, additionalargs))

	body = makeBody(''.join(statements))

	funcname = 'visitChildren'
	if reverse:
		funcname += 'Reversed'

	if forced:
		funcname += 'Forced'

	code = "def %s(%s):\n%s" % (funcname, args, body)
		
	return code


def makeRewrite(clsname, desc, reverse=False, mutate=False, shared=False, vargs=False, kargs=False):
	args = "self, _callback"

	statements = []
	
	additionalargs = ''
	if vargs:
		additionalargs += ', *vargs'
	if kargs:
		additionalargs += ', **kargs'
	args += additionalargs
	
	if not shared or mutate:
		iterator = reversed(desc) if reverse else desc
		
		uid = 0	
		targets = []
		mutation = []
		
		for field in iterator:
			target = "_%d" % uid
			uid += 1
			targets.append(target)
			
			if field.repeated:
				expr = '[_callback(_child%s) for _child in self.%s]' % (additionalargs, field.internalname)
			else:
				expr = '_callback(self.%s%s)' % (field.internalname, additionalargs)
	
			if field.optional:
				expr += " if self.%s is not None else None" % field.internalname
			
			statements.append("\t%s = %s\n" % (target, expr))
	
			if mutate:
				mutation.append("\tself.%s = %s\n"  % (field.internalname, target))
	
		if mutate:
			statements.extend(mutation)
			statements.append("\treturn self\n")		
		else:
			statements.append("\tresult = %s(%s)\n" % (clsname, ", ".join(targets)))
			statements.append("\tresult.annotation = self.annotation\n")
			statements.append("\treturn result\n")
	else:
		# rewriting a shared node, but not mutating it... do nothing.
		statements.append("\treturn self\n")		

	body = makeBody(''.join(statements))

	funcname = "replaceChildren" if mutate else "rewriteChildren"
		
	if reverse:
		funcname += 'Reversed'
		
	code = "def %s(%s):\n%s" % (funcname, args, body)
	
	return code