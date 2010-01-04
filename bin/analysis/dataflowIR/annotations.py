class CorrelatedAnnotation(object):
	__slots__ = 'flat', 'correlated'
	def __init__(self, flat, correlated):
		self.flat = flat
		self.correlated = correlated


class DataflowAnnotation(object):
	__slots__ = ()

	def rewrite(self, **kwds):
		# Make sure extraneous keywords were not given.
		for name in kwds.iterkeys():
			assert name in self.__slots__, name

		values = {}
		for name in self.__slots__:
			if name in kwds:
				value = kwds[name]
			else:
				value = getattr(self, name)
			values[name] = value

		return type(self)(**values)


class DataflowOpAnnotation(DataflowAnnotation):
	__slots__ = 'read', 'modify', 'allocate', 'mask'

	def __init__(self, read, modify, allocate, mask):
		self.read     = read
		self.modify   = modify
		self.allocate = allocate
		self.mask     = mask


class DataflowSlotAnnotation(DataflowAnnotation):
	__slots__ = 'values', 'unique'

	def __init__(self, values, unique):
		self.values = values
		self.unique = unique


class DataflowObjectAnnotation(DataflowAnnotation):
	__slots__ = 'preexisting', 'unique', 'mask', 'final'

	def __init__(self, preexisting, unique, mask, final):
		self.preexisting = preexisting
		self.unique      = unique
		self.mask        = mask
		self.final       = final
