from util.asttools.annotation import Annotation

class ObjectAnnotation(Annotation):
	__slots__ = 'preexisting', 'unique', 'final',

	def __init__(self, preexisting, unique, final):
		self.preexisting = preexisting
		self.unique      = unique
		self.final       = final

class FieldAnnotation(Annotation):
	__slots__ = 'unique',

	def __init__(self, unique):
		self.unique = unique

emptyFieldAnnotation  = FieldAnnotation(False)
emptyObjectAnnotation = ObjectAnnotation(False, False, False)
