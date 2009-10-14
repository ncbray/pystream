class CorrelatedAnnotation(object):
	__slots__ = 'flat', 'correlated'
	def __init__(self, flat, correlated):
		self.flat = flat
		self.correlated = correlated


class DataflowAnnotation(object):
	__slots__ = ()

	
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
	__slots__ = 'preexisting', 'unique', 'mask'
	
	def __init__(self, preexisting, unique, mask):
		self.preexisting = preexisting
		self.unique = unique
		self.mask = mask