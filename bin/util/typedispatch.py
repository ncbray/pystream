__all__ = [
		'TypeDispatcher', 'defaultdispatch', 'dispatch',
		'TypeDispatchError', 'TypeDispatchDeclarationError'
		]

import inspect

def flattenTypesInto(l, result):
	for child in l:
		if isinstance(child, (list, tuple)):
			flattenTypesInto(child, result)
		else:
			if not isinstance(child, type):
				raise TypeDispatchDeclarationError, "Expected a type, got %r instead." % child
			result.append(child)

def dispatch(*types):
	def dispatchF(f):
		def dispatchWrap(*args, **kargs):
			return f(*args, **kargs)
		dispatchWrap.__original__ = f
		dispatchWrap.__dispatch__ = []
		flattenTypesInto(types, dispatchWrap.__dispatch__)
		return dispatchWrap
	return dispatchF


def defaultdispatch(f):
	def defaultWrap(*args, **kargs):
		return f(*args, **kargs)
	defaultWrap.__original__ = f
	defaultWrap.__dispatch__ = (None,)
	return defaultWrap


def dispatch__call__(self, p, *args):
	t = type(p)
	table = self.__typeDispatchTable__

	func = table.get(t)

	if func is None:
		# Search for a matching superclass
		# This should occur only once per class.

		if self.__concrete__:
			possible = (t,)
		else:
			possible = t.mro()

		for supercls in possible:
			func = table.get(supercls)

			if func is not None:
				break
			elif self.__namedispatch__:
				# The emulates "visitor" dispatch, to allow for evolutionary refactoring
				name = self.__nameprefix__ + t.__name__
				func = type(self).__dict__.get(name)

				if func is not None:
					break

		# default
		if func is None:
			func = table.get(None)

		# Cache the function that we found
		table[t] = func

	return func(self, p, *args)


class TypeDispatchError(Exception):
	pass

class TypeDispatchDeclarationError(Exception):
	pass


def exceptionDefault(self, node, *args):
	raise TypeDispatchError, "%r cannot handle %r\n%r" % (type(self), type(node), node)


def inlineAncestor(t, lut):
	if hasattr(t, '__typeDispatchTable__'):
		# Search for types that haven't been defined, yet.
		for k, v in t.__typeDispatchTable__.iteritems():
			if k not in lut:
				lut[k] = v

class typedispatcher(type):
	def __new__(self, name, bases, d):
		lut = {}
		restore = {}

		# Build the type lookup table from the local declaration
		for k, v in d.iteritems():
			if hasattr(v, '__dispatch__') and hasattr(v, '__original__'):
				types = v.__dispatch__
				original = v.__original__

				for t in types:
					if t in lut:
						raise TypeDispatchDeclarationError, "%s has declared with multiple handlers for type %s" % (name, t.__name__)
					else:
						lut[t] = original

				restore[k] = original

		# Remove the wrappers from the methods
		d.update(restore)

		# Search and inline dispatch tables from the MRO
		for base in bases:
			for t in inspect.getmro(base):
				inlineAncestor(t, lut)

		if None not in lut:
			raise TypeDispatchDeclarationError, "%s has no default dispatch" % (name,)

		d['__typeDispatchTable__'] = lut

		return type.__new__(self, name, bases, d)

class TypeDispatcher(object):
	__metaclass__    = typedispatcher
	__dispatch__     = dispatch__call__
	__call__         = dispatch__call__
	exceptionDefault = defaultdispatch(exceptionDefault)
	__concrete__     = False

	__namedispatch__ = False
	__nameprefix__   = 'visit'
