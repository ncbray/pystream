# Copyright 2011 Nicholas Bray
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
		output.append('%sif isinstance(%s, (list, tuple)):\n' % (tabs, field))
		output.append('%s\tfor _i in %s:\n' % (tabs, field))
		makeScalarTypecheckStatement(name, field+'[]', '_i', tn, optional, tabs+'\t\t', output)
		output.append('%selif not isinstance(%s, SymbolBase):\n' % (tabs, field))
		output.append('%s\t%s\n' % (tabs, raiseTypeError(name, '(list, tuple, SymbolBase)', field, field)))
	else:
		makeScalarTypecheckStatement(name, field, field, tn, optional, tabs, output)


def makeInitStatements(clsname, desc, dopostinit):
	inits = []
	for field in desc:
		if field.type:
			tn = typeName(field.type)
			makeTypecheckStatement(clsname, field.name, tn, field.optional, field.repeated, '\t', inits)
		elif not field.optional:
			inits.append('\tassert %s is not None, "Field %s.%s is not optional."\n' % (field.name, clsname, field.name))

		inits.append('\tself.%s = %s\n' % (field.internalname, field.name))

	if dopostinit:
		inits.append('\tself.__postinit__()\n')

	return inits

def argsFromDesc(desc):
	if desc:
		fieldstr = ", ".join([field.name for field in desc])
		args = ", ".join(('self', fieldstr))
	else:
		args = 'self'
	return args

def makeBody(code):
	if not code:
		return '\tpass\n'
	else:
		return code

def makeInit(name, desc, dopostinit):
	inits = makeInitStatements(name, desc, dopostinit)
	inits.append('\tself.annotation = self.__emptyAnnotation__')

	args = argsFromDesc(desc)

	# NOTE super.__init__ should be a no-op, as we're initializing all the fields, anyways?
	#code = "def __init__(%s):\n\tsuper(%s, self).__init__()\n%s" % (args, name, ''.join(inits))
	code = "def __init__(%s):\n%s" % (args, ''.join(inits))
	return code


def makeReplaceChildren(name, desc, dopostinit):
	inits = makeInitStatements(name, desc, dopostinit)

	args = argsFromDesc(desc)

	body = makeBody(''.join(inits))

	code = "def _replaceChildren(%s):\n%s" % (args, body)
	return code

def makeRepr(name, desc):
	interp = ", ".join(['%r']*len(desc))
	fields = " ".join("self.%s,"%field.internalname for field in desc)

	code = """def __repr__(self):
	return "%s(%s)" %% (%s)
""" % (name, interp, fields)

	return code

# To prevent possible recursion, shared node do NOT print their children.
def makeSharedRepr(name, desc):
	code = """def __repr__(self):
	return "%s(%%d)" %% (id(self),)
""" % (name)

	return code


def makeAccept(name):
	code = """def accept(self, visitor, *args):
	return visitor.visit%s(self, *args)
""" % (name)

	return code

def makeGetChildren(desc):
	children = ' '.join(["self.%s," % field.internalname for field in desc])
	code = """def children(self):
	return (%s)
""" % (children)

	return code


def makeGetFields(desc):
	children = ' '.join(["(%r, self.%s)," % (field.name, field.internalname) for field in desc])
	code = """def fields(self):
	return (%s)
""" % (children)

	return code

def makeSetter(clsname, field):
	inits = []

	tn = typeName(field.type)
	makeTypecheckStatement(clsname, field.name, tn, field.optional, field.repeated, '\t', inits)
	inits.append('\tself.%s = %s\n' % (field.internalname, field.name))

	code = "def __set_%s__(self, %s):\n%s" % (field.name, field.name, ''.join(inits))
	return code

def makeGetter(clsname, desc):
	code = "def __get_%s__(self):\n\treturn self.%s\n" % (desc.name, desc.internalname)
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
				if reverse:
					statements.append('%sfor _child in reversed(self.%s):\n' % (indent, field.internalname))
				else:
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


def makeRewrite(clsname, desc, reverse=False, mutate=False, shared=False, forced=False, vargs=False, kargs=False):
	assert not (mutate and forced), clsname
	assert not forced or shared, clsname

	args = "self, _callback"

	statements = []

	additionalargs = ''
	if vargs:
		additionalargs += ', *vargs'
	if kargs:
		additionalargs += ', **kargs'
	args += additionalargs

	if not shared or mutate or forced:
		iterator = reversed(desc) if reverse else desc

		uid = 0
		targets = []
		mutation = []

		for field in iterator:
			target = "_%d" % uid
			uid += 1
			targets.append(target)

			if field.repeated:
				childexpr = '_callback(_child%s)' % (additionalargs,)
				if field.optional:
					childexpr += ' if _child is not None else None'

				if reverse:
					expr = 'list(reversed([%s for _child in reversed(self.%s)]))' % (childexpr, field.internalname)
				else:
					expr = '[%s for _child in self.%s]' % (childexpr, field.internalname)

				# Guard against symbols
				expr = '_callback(self.%s%s) if isinstance(self.%s, SymbolBase) else %s' % (field.internalname, additionalargs, field.internalname, expr)
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
			if reverse: targets.reverse()

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

	if forced:
		funcname += 'Forced'

	code = "def %s(%s):\n%s" % (funcname, args, body)

	return code
