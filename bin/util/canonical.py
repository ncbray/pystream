# An object that is equivalent if its "canonical values" are equivalent.
class CanonicalObject(object):
	__slots__ = 'canonical', 'hash'

	def __init__(self, *args):
		self.setCanonical(*args)

	def setCanonical(self, *args):
		self.canonical = args
		self.hash = id(type(self))^hash(args)

	def __hash__(self):
		return self.hash

	def __eq__(self, other):
		return type(self) == type(other) and self.canonical == other.canonical

	def __repr__(self):
		canonicalStr = ", ".join([repr(obj) for obj in self.canonical])
		return "%s(%s)" % (type(self).__name__, canonicalStr)

# Assumes that the same arguments will create the same object,
# and different arguments will create different objects.
class CanonicalCache(object):
	def __init__(self, create):
		self.create = create
		self.cache = {}

	def __call__(self, *args):
		if args not in self.cache:
			obj = self.create(*args)
			self.cache[args] = obj
			return obj
		else:
			return self.cache[args]

	def get(self, *args):
		return self(*args)

	def exists(self, *args):
		return args in self.cache