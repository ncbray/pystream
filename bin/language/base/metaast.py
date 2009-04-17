__all__ = ['astnode', 'ASTNode', 'Symbol', 'children',
	   'reconstruct', 'makeASTManifest',
	   'astequal', 'asthash',]

# A metaclass for generating AST node classes.

import sys

from . import codegeneration

doTypeChecks = False

class ClassBuilder(object):
	def __init__(self, type, name, bases, d):
		self.type  = type
		self.name  = name
		self.bases = bases
		self.d     = d

		self.types    = {}
		self.optional = set()
		self.repeated = set()

	def getShared(self):
		shared = bool(self.d.get('__shared__', False))
		self.d['__shared__'] = shared
		return shared

	def getGlobalDict(self):
		module = self.d['__module__']
		assert module in sys.modules
		g = sys.modules[module].__dict__
		return g

	def getFields(self):
		# Process the fields
		if '__fields__' not in self.d:
			fields = ()
			self.d['__fields__'] = fields
		else:
			fields = self.d['__fields__']

			if isinstance(fields, str):
				fields = tuple(fields.strip().split())
				self.d['__fields__'] = fields

		parsedFields = []
		for field in fields:
			optional = False
			repeated = False
			type     = None

			if field[-1] == '?':
				optional = True
				field = field[:-1]
			else:
				optional = False

			if field[-1] == '*':
				repeated = True
				field = field[:-1]
			else:
				repeated = False


			parts = field.split(':')

			name = parts[0]
			parsedFields.append(name)

			# Is the field typed?
			if len(parts) > 1 and parts[1]:
				self.types[name] = parts[1]

			# Mark the field as optional?
			if optional:
				self.optional.add(name)

			# Mark the field as repeated?
			if repeated:
				self.repeated.add(name)

		return tuple(parsedFields)

	def getTypes(self, fields):
		# Process the field types
		if '__types__' not in self.d:
			types = {}
			self.d['__types__'] = types
		else:
			types = self.d['__types__']

		types.update(self.types)

		assert isinstance(types, dict), types

		for k in types.iterkeys():
			assert k in fields, "Typed field %r is does not exist." % k

		return types

	def getOptional(self, fields):
		optional = self.d.get('__optional__', ())

		if isinstance(optional, str):
			optional =  tuple(optional.strip().split())

		optional = frozenset(self.optional.union(optional))

		self.d['__optional__'] = optional

		for k in optional:
			assert k in fields, "Optional field %s is does not exist." % k

		return optional

	def makeWrappedFieldSlots(self, fields, types, optional):
		slots = ["_%s" % field for field in fields]

		for field in fields:
			getter = self.makeFunc(codegeneration.makeGetter, (self.name, field))
			setter = self.makeFunc(codegeneration.makeSetter, (self.name, field, types.get(field), field in optional, field in self.repeated))
			self.d[field] = property(getter, setter)

		return slots

	def makeDirectFieldSlots(self, fields, types, optional):
		return [field for field in fields]

	def makeFieldSlots(self, fields, types, optional):
		# Create slots for the fields.
		if doTypeChecks:
			return self.makeWrappedFieldSlots(fields, types, optional)
		else:
			return self.makeDirectFieldSlots(fields, types, optional)

	def appendToExistingSlots(self, slots):
		# Prepend the fields to the existing slots declaration.
		existing = self.d.get('__slots__', ())
		if isinstance(existing, str):
			existing = (existing,)

		slots.extend(existing)
		self.d['__slots__'] = tuple(slots)
		return slots


	def finalize(self):
		return type.__new__(self.type, self.name, self.bases, self.d)

	def makeFunc(self, func, args):
		return codegeneration.compileFunc(func(*args), self.g)

	def defaultFunc(self, name, func, args):
		if not name in self.d:
			self.d[name] = self.makeFunc(func, args)

	def addDefaultMethods(self, fields, types, optional):
		# Generate and attach methods.
		self.defaultFunc('__init__', codegeneration.makeInit, (self.name, fields, types, optional, self.repeated))
		self.defaultFunc('__repr__', codegeneration.makeRepr, (self.name, fields))
		self.defaultFunc('accept',   codegeneration.makeAccept, (self.name,))
		self.defaultFunc('children', codegeneration.makeGetChildren, (fields,))
		self.defaultFunc('fields',   codegeneration.makeGetFields, (fields,))

		self.defaultFunc('replaceChildren', codegeneration.makeReplaceChildren, (self.name, fields, types, optional, self.repeated))

		self.defaultFunc('asteq', codegeneration.makeEq, (fields,))
		self.defaultFunc('asthash', codegeneration.makeHash, (fields,))


	def mutate(self):
		self.g   = self.getGlobalDict()

		fields   = self.getFields()
		types    = self.getTypes(fields)
		optional = self.getOptional(fields)

		shared   = self.getShared()

		slots = self.makeFieldSlots(fields, types, optional)
		slots = self.appendToExistingSlots(slots)

		self.addDefaultMethods(fields, types, optional)

		return self

	def build(self):
		return self.mutate().finalize()

# TODO grab fields from bases?

class astnode(type):
	def __new__(mcls, name, bases, d):
		return ClassBuilder(mcls, name, bases, d).build()


def makeASTManifest(glbls):
	manifest = {}
	for name, obj in glbls.iteritems():
		if isinstance(obj, type) and hasattr(obj, '__metaclass__'):
			if obj.__metaclass__ == astnode:
				manifest[name] = obj
	return manifest


LeafTypes = (str, type(None), bool, int, long, float)
ListTypes = (list, tuple)

def children(node):
	if isinstance(node, LeafTypes):
		return ()
	elif isinstance(node, ListTypes):
		return node
	else:
		return node.children()

def reconstruct(node, newchildren):
	if isinstance(node, LeafTypes):
		assert not newchildren, newchildren
		return node
	elif isinstance(node, ListTypes):
		return type(node)(newchildren)
	else:
		try:
			newnode = type(node)(*newchildren)
			assert hasattr(node, 'annotation'), node
			newnode.annotation = node.annotation
			return newnode
		except:
			print "error", node
			print newchildren
			raise

def astequal(a, b):
	if isinstance(a, LeafTypes) and isinstance(b, LeafTypes):
		return a == b
	elif type(a) is type(b):
		ca, cb = children(a), children(b)
		if len(ca) == len(cb):
			for x, y in zip(ca, cb):
				if not astequal(x, y):
					return False
			return True
	return False

def asthash(node):
	if isinstance(node, LeafTypes):
		return hash(node)
	else:
		return id(type(node))^hash(tuple(node.children))

class Symbol(object):
	__metaclass__ = astnode
	__slots__    = 'name'

	def __init__(self, name):
		assert isinstance(name, str)
		self.name = name

	def __repr__(self):
		return "Symbol(%s)" % self.name

class ASTNode(object):
	__metaclass__ = astnode
	__slots__ = 'annotation'

	emptyAnnotation = None

	def __init__(self):
		self.annotation = self.emptyAnnotation

	def rewriteAnnotation(self, **kwds):
		self.annotation = self.annotation.rewrite(**kwds)
