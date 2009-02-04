import util.canonical
CanonicalObject = util.canonical.CanonicalObject

from programIR.python import program

# Extended types are names for objects that cannot be merged by the analysis.


# Abstract base class
class ExtendedType(CanonicalObject):
	__slots__ = ()

	def isExisting(self):
		return False

	def isExternal(self):
		return False

	def group(self):
		return self

# All extended types may as well have an "obj" slot,
# as the type of an object won't change.
class ExtendedObjectType(ExtendedType):
	__slots__ = 'obj'
	def __init__(self, obj):
		assert isinstance(obj, program.AbstractObject), type(obj)
		self.obj = obj
		self.setCanonical(obj)

	def group(self):
		return self.obj


# Passed in as an argument
class ExternalObjectType(ExtendedObjectType):
	__slots__ = ()

	def isExternal(self):
		return True

	def __repr__(self):
		return "<external %r>" % self.obj


# Found in memory by the decompiler
class ExistingObjectType(ExtendedObjectType):
	__slots__ = ()

	def isExisting(self):
		return True

	def __repr__(self):
		return "<existing %r>" % self.obj


# The basic extended type, even when the analysis is not path sensitive
# (the path will simply be None)
class PathObjectType(ExtendedObjectType):
	__slots__ = ('path',)

	def __init__(self, path, obj):
		assert isinstance(obj, program.AbstractObject)
		self.path = path
		self.obj  = obj
		self.setCanonical(path, obj)

	def __repr__(self):
		if self.path is None:
			return "<path * %r>" % self.obj
		else:
			return "<path %d %r>" % (id(self.path), self.obj)

# Methods are typed according to the function and instance they are bound to
# TODO prevent type loops
class MethodObjectType(ExtendedObjectType):
	__slots__ = 'func', 'inst'

	def __init__(self, func, inst, obj):
		assert isinstance(func, ExtendedType)
		assert isinstance(inst, ExtendedType)
		assert isinstance(obj, program.AbstractObject)
		self.func = func
		self.inst = inst
		self.obj  = obj
		self.setCanonical(func, inst, obj)

	def __repr__(self):
		return "<method %s %d %r>" % (id(self.func), id(self.inst), self.obj)

# Extended parameter objects need to be kept precise per context
# TODO make this based on the full context?
# TODO prevent type loops
class ContextObjectType(ExtendedObjectType):
	__slots__ = 'context'

	def __init__(self, context, obj):
		assert isinstance(obj, program.AbstractObject)
		self.context = context
		self.obj = obj
		self.setCanonical(context, obj)

	def __repr__(self):
		return "<context %d %r>" % (id(self.context), self.obj)