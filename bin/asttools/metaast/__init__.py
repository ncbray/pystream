__all__ = ['ASTNode',]

# A metaclass for generating AST node classes.

import sys

from . import codegeneration

class FieldDescriptor(object):
	__slots__ = 'name', 'internalname', 'type', 'optional', 'repeated'
	
	def __init__(self, name, internalname, t, optional, repeated):
		self.name = name
		self.internalname = internalname
		self.type = t
		self.optional = optional
		self.repeated = repeated

	def __repr__(self):
		return "astfield(%r, %r, %r, %r, %r)" % (self.name, self.internalname, self.type, self.optional, self.repeated)

# Enforces mutability, but slows down the program.
wrapProperties = False

class ClassBuilder(object):
	def __init__(self, type, name, bases, d):
		self.type  = type
		self.name  = name
		self.bases = bases
		self.d     = d

		self.types    = {}
		self.optional = set()
		self.repeated = set()

	def hasAttr(self, attr):
		if attr in self.d:
			return True

		for base in self.bases:
			if hasattr(base, attr):
				return True

		return False

	def getAttr(self, attr, default):
		if attr in self.d:
			return self.d[attr]

		for base in self.bases:
			for cls in base.mro():
				if attr in cls.__dict__:
					return cls.__dict__[attr]
		return default

	def getShared(self):
		shared = bool(self.getAttr('__shared__', False))
		self.d['__shared__'] = shared
		return shared

	def getMutable(self, shared):
		mutable = True if shared else bool(self.getAttr('__mutable__', False))
		self.d['__mutable__'] = mutable
		return mutable

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

		for field, slot in zip(fields, slots):
			getter = self.makeFunc(codegeneration.makeGetter, (self.name, field, slot))

			if self.mutable:
				setter = self.makeFunc(codegeneration.makeSetter, (self.name, field, slot, types.get(field), field in optional, field in self.repeated))
				p = property(getter, setter)
			else:
				p = property(getter)

			self.d[field] = p

		return slots

	def makeDirectFieldSlots(self, fields, types, optional):
		return [field for field in fields]

	def makeFieldSlots(self, fields, types, optional):
		# Create slots for the fields.
		if wrapProperties:
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

	def makeFunc(self, func, args, kargs):
		code = func(*args, **kargs)
		#print code
		#print
		return codegeneration.compileFunc(self.name, code, self.g)

	def defaultFunc(self, name, func, args, kargs={}):
		if not name in self.d:
			self.d[name] = self.makeFunc(func, args, kargs)

	def addDefaultMethods(self, desc, paramnames, fields, types, optional, shared):
		dopostinit = self.hasAttr('__postinit__')

		# Generate and attach methods.
		self.defaultFunc('__init__', codegeneration.makeInit, (self.name, paramnames, fields, types, optional, self.repeated, dopostinit))

		if shared:
			self.defaultFunc('__repr__', codegeneration.makeSharedRepr, (self.name, fields))
		else:
			self.defaultFunc('__repr__', codegeneration.makeRepr, (self.name, fields))
		self.defaultFunc('accept',   codegeneration.makeAccept, (self.name,))
		self.defaultFunc('children', codegeneration.makeGetChildren, (fields,))
		self.defaultFunc('fields',   codegeneration.makeGetFields, (paramnames, fields,))

		if self.mutable:
			self.defaultFunc('_replaceChildren', codegeneration.makeReplaceChildren, (self.name, paramnames, fields, types, optional, self.repeated, dopostinit))

		self.defaultFunc('visitChildren', codegeneration.makeVisit, (self.name, desc), {'reverse':False, 'shared':shared})
		self.defaultFunc('visitChildrenReversed', codegeneration.makeVisit, (self.name, desc), {'reverse':True, 'shared':shared})

		if self.mutable:
			self.defaultFunc('visitChildrenForced', codegeneration.makeVisit, (self.name, desc), {'reverse':False, 'shared':shared, 'forced':True})
			self.defaultFunc('visitChildrenReversedForced', codegeneration.makeVisit, (self.name, desc), {'reverse':True, 'shared':shared, 'forced':True})

		# For the sake of uniformity, shared nodes are given a rewrite method even though it does nothing.
		self.defaultFunc('rewriteChildren', codegeneration.makeRewrite, (self.name, desc), {'reverse':False, 'shared':shared, 'mutate':False, 'vargs':False, 'kargs':False})
		self.defaultFunc('rewriteChildrenReversed', codegeneration.makeRewrite, (self.name, desc), {'reverse':True, 'shared':shared, 'mutate':False, 'vargs':False, 'kargs':False})

		if self.mutable:
			self.defaultFunc('replaceChildren', codegeneration.makeRewrite, (self.name, desc), {'reverse':False, 'shared':shared, 'mutate':True, 'vargs':False, 'kargs':False})
			self.defaultFunc('replaceChildrenReversed', codegeneration.makeRewrite, (self.name, desc), {'reverse':True, 'shared':shared, 'mutate':True, 'vargs':False, 'kargs':False})



	def mutate(self):
		self.g   = self.getGlobalDict()

		fields   = self.getFields()
		types    = self.getTypes(fields)
		optional = self.getOptional(fields)

		shared   = self.getShared()
		self.mutable = self.getMutable(shared)

		slots = self.makeFieldSlots(fields, types, optional)
		internalNames = list(slots)
		slots = self.appendToExistingSlots(slots)

		desc = []
		for name, internal in zip(fields, internalNames):
			desc.append(FieldDescriptor(name, internal, types.get(name), name in optional, name in self.repeated))

		self.addDefaultMethods(desc, fields, internalNames, types, optional, shared)

		return self

	def build(self):
		return self.mutate().finalize()


class astnode(type):
	def __new__(self, name, bases, d):
		return ClassBuilder(self, name, bases, d).build()

class ASTNode(object):
	__metaclass__ = astnode
	__slots__ = 'annotation'

	__emptyAnnotation__ = None
	__leaf__ = False # For pretty printing

	def __init__(self):
		self.annotation = self.__emptyAnnotation__

	def rewriteAnnotation(self, **kwds):
		self.annotation = self.annotation.rewrite(**kwds)

	def reconstruct(self, *newchildren):
		newnode = type(self)(*newchildren)
		newnode.annotation = self.annotation
		return newnode

	def clone(self):
		return self.reconstruct(*self.children())
