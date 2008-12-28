__all__ = ['typedispatcher', 'defaultdispatch', 'dispatch', 'allChildren']

from xform import allChildren

def dispatch(*types):
	def dispatchF(f):
		def dispatchWrap(*args, **kargs):
			return f(*args, **kargs)
		dispatchWrap.__original__ = f
		dispatchWrap.__dispatch__ = types
		return dispatchWrap
	return dispatchF


def defaultdispatch(f):
	def defaultWrap(*args, **kargs):
		return f(*args, **kargs)
	defaultWrap.__original__ = f
	defaultWrap.__dispatch__ = 'default'
	return defaultWrap

def dispatch__call__(self, p, *args):
	t = type(p)
	
	if not t in self.__dispatchTable__:
		# Binds method.
		return self.__dispatchDefault__(p, *args)
	else:
		# Does not bind method.
		return self.__dispatchTable__[t](self, p, *args)
	

def null(self, p, *args):
	return p

def typedispatcher(name, bases, d):

	lut = {}
	restore = {}

	default = null
	
	for k, v in d.iteritems():
		if hasattr(v, '__dispatch__') and hasattr(v, '__original__'):
			types = v.__dispatch__
			original = v.__original__

			if types == 'default':
				default = original
			else:
				for t in types:
					assert not t in lut, (name, t)
					lut[t] = original
			restore[k] = original

	d.update(restore)

	d['__dispatchTable__'] = lut
	d['__dispatchDefault__'] = default
	d['__call__'] = dispatch__call__
		
	return type(name, bases, d)
