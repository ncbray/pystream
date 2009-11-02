__all__ = ('singleton', 'instance')

class singletonMetaclass(type):
	def __new__(self, name, bases, d):
		if '__repr__' not in d:
			def __repr__(self):
				return name
			d['__repr__'] = __repr__
		cls = type.__new__(self, name+'Type', bases, d)
		return cls()

class singleton(object):
	__metaclass__ = singletonMetaclass
	__slots__ = ()

singleton = type(singleton)


# A decorator for turning a class into a psedo-singleton
# Handy for stateless TypeDispatcher classes
def instance(cls):
	cls.__name__ += 'Type'
	return cls()
