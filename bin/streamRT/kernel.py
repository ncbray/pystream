from __future__ import absolute_import

import new

def shouldIterate(o, role):
	return isinstance(o, stream) and role != 'uniform'

class StreamMismatchError(Exception):
	pass

# Used to generated debug info if checkStreams fails.
def getLengths(args):
	lengths = []
	for arg in args:
		if isinstance(arg, stream):
			lengths.append(len(arg))
		else:
			lengths.append(None)
	return lengths

# Check for stream arguments.
# If there's more than one, check that they're the same length.
def checkStreams(args, config):
	streams = False
	length = 0
	
	for arg, role in zip(args, config.roles):
		if shouldIterate(arg, role):
			if not streams:
				length = len(arg)
				streams = True
			elif length != len(arg):
				lengths = getLengths(args)
				raise StreamMismatchError, "Kernel called with streams of different lengths: %s" % str(tuple(lengths))
	return streams




class UniformIterator(object):
	__slots__ = 'value'
	def __init__(self, value):
		self.value = value

	def __iter__(self):
		return self

	def next(self):
		return self.value
		
def getStreamIterator(o, role):
	if shouldIterate(o, role):
		return iter(o)
	else:
		return UniformIterator(o)

def argiterator(args, config):
	args = [getStreamIterator(arg, role) for arg, role in zip(args, config.roles)]
	while args:
		yield [it.next() for it in args]


class kernel(object):
	__slots__ = 'f', 'config'
	
	def __init__(self, f, config):
		self.f = f
		self.config = config

	def __call__(self, *args):
		if checkStreams(args, self.config):
			out = []
			for iterargs in argiterator(args, self.config):
				out.append(self.f(*iterargs))
			return stream(out)
		else:	
			return self.f(*args)

	def __get__(self, instance, owner):
		return new.instancemethod(self, instance, owner)

uniform = 'uniform'
default = 'default'
		

def getArgnames(f):
	code = f.func_code
	return code.co_varnames[:code.co_argcount]

class KernelConfiguration(object):
	__slots__ = 'unpack', 'roles'
	def __init__(self, unpack, roles):
		self.unpack = unpack
		self.roles  = roles
				


class KernelConfigAccumulator(object):
	__slots__ = '_roles', '_unpack'
	def __init__(self):
		self._roles = {}
		self._unpack = False

	@property
	def unpack(self):
		self._unpack = True

	def roles(self, **kargs):
		self._roles = kargs
		
	def __call__(self, f):
		assert callable(f)
		return kernelcls(f, self.__createConfig(f))

	def __createConfig(self, f):
		argnames = getArgnames(f)

		roleList = []
		for name in argnames:
			if name in self._roles:
				roleList.append(self._roles[name])
			else:
				roleList.append(default)

		return KernelConfiguration(self._unpack, roleList)

				

class KernelDecorator(object):
	__slots__ = ()
	def roles(self, **kargs):
		accum = KernelConfigAccumulator()
		accum.roles(**kargs)
		return accum

	@property
	def unpack(self):
		accum = KernelConfigAccumulator()
		accum.unpack
		return accum
		
	def __call__(self, *args, **kargs):
		accum = KernelConfigAccumulator()
		
		if len(args) == 1 and len(kargs) == 0 and callable(args[0]):
			# decorator called directly on function.
			return accum(args[0])
		elif len(args) == 0 and len(kargs) > 0:
			accum.roles(**kargs)
			return accum
		else:
			assert False

kerneldecorator = KernelDecorator()


# HACK
kernelcls = kernel
kernel = kerneldecorator

class stream(object):
	__slots__ = 'elements'
	def __init__(self, l=None):
		if l == None:
			self.elements = []
		else:
			assert isinstance(l, list)
			self.elements = l

	def __getitem__(self, key):
		return self.elements[key]

	def __len__(self):
		return len(self.elements)

	def __iter__(self):
		return iter(self.elements)

	# HACK?
	def append(self, value):
		self.elements.append(value)

	# Check writeability?
	def push(self, value):
		self.elements.append(value)

	@kernel
	def __add__(self, other):
		return self+other

	@kernel
	def __sub__(self, other):
		return self-other

	@kernel
	def __mul__(self, other):
		return self*other

	@kernel
	def __div__(self, other):
		return self/other

	@kernel
	def __floordiv__(self, other):
		return self//other

	@kernel
	def __mod__(self, other):
		return self%other

	@kernel
	def __divmod__(self, other):
		return divmod(self, other)


	@kernel
	def __pow__(self, other, modulo=None):
		if modulo == None:
			return self**other
		else:
			return pow(self, other, modulo)

	# Binary: lshift, rshift, and, or, xor
	#

	@kernel
	def __radd__(self, other):
		return other+self

	@kernel
	def __rsub__(self, other):
		return other-self

	@kernel
	def __rmul__(self, other):
		return other*self

	@kernel
	def __rdiv__(self, other):
		return other/self
