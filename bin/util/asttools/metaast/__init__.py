__all__ = ['ASTNode', 'SymbolBase']

# A metaclass for generating AST node classes.

import sys
import re
from . import codegeneration
from .. symbols import SymbolBase

### The field parser ###

fieldFinder = re.compile('(\w+)(?::(\w+|\([^\)]*\)))?(\?)?(\*)?') # Matches name, type, optional, repeated
typeSplitter = re.compile('[,\s]\s*')

def parseFields(s, addSymbolType=True):
	if isinstance(s, tuple):
		fields = []
		for part in s:
			fields.extend(parseFields(part, addSymbolType))
		return fields

	fields = fieldFinder.findall(s)

	result = []

	for field in fields:
		# Break the types apart
		types = typeSplitter.split(field[1].strip('()'))
		# Filter out empty strings
		types = [t for t in types if t]

		# If the AST supports symbolic matching, and the field is typed, add the symbol type
		if types and addSymbolType and 'SymbolBase' not in types:
			types.append('SymbolBase')

		optional = bool(field[2])
		repeated = bool(field[3])

		if wrapProperties:
			internal = '_'+field[0]
		else:
			internal = field[0]

		result.append(FieldDescriptor(field[0], internal, tuple(types), optional, repeated))

	return result

class FieldDescriptor(object):
	__slots__ = 'name', 'internalname', 'type', 'optional', 'repeated'

	def __init__(self, name, internalname, t, optional, repeated):
		self.name = name
		self.internalname = internalname
		self.type = t
		self.optional = optional
		self.repeated = repeated

	def __repr__(self):
		return "astfield(%r, %r, %r, optional=%r, repeated=%r)" % (self.name, self.internalname, self.type, self.optional, self.repeated)

# Enforces mutability, but slows down the program.
wrapProperties = False

class ClassBuilder(object):
	def __init__(self, type, name, bases, d):
		self.type  = type
		self.name  = name
		self.bases = bases
		self.d     = d

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

		return parseFields(fields)

	def makeWrappedFieldSlots(self, desc):
		for field in desc:
			getter = self.makeFunc(codegeneration.makeGetter, (self.name, field), {})

			if self.mutable:
				setter = self.makeFunc(codegeneration.makeSetter, (self.name, field), {})
				p = property(getter, setter)
			else:
				p = property(getter)

			self.d[field.name] = p

	def makeFieldSlots(self, desc):
		# Create slots for the fields.
		if wrapProperties:
			self.makeWrappedFieldSlots(desc)
		return [field.internalname for field in desc]

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

	def copyFunc(self, src, dst):
		if not dst in self.d:
			self.d[dst] = self.d[src]

	def addDefaultMethods(self, desc, shared):
		dopostinit = self.hasAttr('__postinit__')

		# Generate and attach methods.
		self.defaultFunc('__init__', codegeneration.makeInit, (self.name, desc, dopostinit))

		if shared:
			self.defaultFunc('__repr__', codegeneration.makeSharedRepr, (self.name, desc))
		else:
			self.defaultFunc('__repr__', codegeneration.makeRepr, (self.name, desc))
		self.defaultFunc('accept',   codegeneration.makeAccept, (self.name,))
		self.defaultFunc('children', codegeneration.makeGetChildren, (desc,))
		self.defaultFunc('fields',   codegeneration.makeGetFields, (desc,))

		self.defaultFunc('visitChildren', codegeneration.makeVisit, (self.name, desc), {'reverse':False, 'shared':shared})
		self.defaultFunc('visitChildrenReversed', codegeneration.makeVisit, (self.name, desc), {'reverse':True, 'shared':shared})

		self.defaultFunc('visitChildrenArgs', codegeneration.makeVisit, (self.name, desc), {'reverse':False, 'shared':shared, 'vargs':True})

		if shared:
			self.defaultFunc('visitChildrenForced', codegeneration.makeVisit, (self.name, desc), {'reverse':False, 'shared':shared, 'forced':True})
			self.defaultFunc('visitChildrenReversedForced', codegeneration.makeVisit, (self.name, desc), {'reverse':True, 'shared':shared, 'forced':True})
			self.defaultFunc('visitChildrenForcedArgs', codegeneration.makeVisit, (self.name, desc), {'reverse':False, 'shared':shared, 'forced':True, 'vargs':True})
		else:
			self.copyFunc('visitChildren', 'visitChildrenForced')
			self.copyFunc('visitChildrenReversed', 'visitChildrenReversedForced')
			self.copyFunc('visitChildrenArgs', 'visitChildrenForcedArgs')

		# For the sake of uniformity, shared nodes are given a rewrite method even though it does nothing.
		self.defaultFunc('rewriteChildren', codegeneration.makeRewrite, (self.name, desc), {'reverse':False, 'shared':shared, 'mutate':False, 'vargs':False, 'kargs':False})
		self.defaultFunc('rewriteChildrenReversed', codegeneration.makeRewrite, (self.name, desc), {'reverse':True, 'shared':shared, 'mutate':False, 'vargs':False, 'kargs':False})

		# Currently rewriteChildren always clones, but this may not be the case in the future.
		self.copyFunc('rewriteChildren', 'rewriteCloned')

		if self.mutable:
			self.defaultFunc('_replaceChildren', codegeneration.makeReplaceChildren, (self.name, desc, dopostinit))
			self.defaultFunc('replaceChildren', codegeneration.makeRewrite, (self.name, desc), {'reverse':False, 'shared':shared, 'mutate':True, 'vargs':False, 'kargs':False})
			self.defaultFunc('replaceChildrenReversed', codegeneration.makeRewrite, (self.name, desc), {'reverse':True, 'shared':shared, 'mutate':True, 'vargs':False, 'kargs':False})

		if shared:
			self.defaultFunc('rewriteChildrenForced', codegeneration.makeRewrite, (self.name, desc), {'reverse':False, 'shared':shared, 'mutate':False, 'forced':True, 'vargs':False, 'kargs':False})


	def mutate(self):
		self.g   = self.getGlobalDict()

		desc   = self.getFields()
		shared = self.getShared()
		self.mutable = self.getMutable(shared)

		slots = self.makeFieldSlots(desc)
		self.appendToExistingSlots(slots)

		self.addDefaultMethods(desc, shared)

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
