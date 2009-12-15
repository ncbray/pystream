from util.monkeypatch import xcollections

class Sentinel(object):
	__slots__ = 'name', '__weakref__'

	def __init__(self, name):
		self.name = name

	def __repr__(self):
		return self.name


# An object that is equivalent if its "canonical values" are equivalent.
class CanonicalObject(object):
	__slots__ = 'canonical', 'hash', '__weakref__'

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


class CanonicalCache(object):
	def __init__(self, create):
		self.create = create
		self.cache  = xcollections.weakcache()

	def __call__(self, *args):
		return self.cache[self.create(*args)]
