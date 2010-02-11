from util.asttools.annotation import Annotation

class ObjectAnnotation(Annotation):
	__slots__ = 'preexisting', 'unique', 'final', 'uniform', 'input'

	def __init__(self, preexisting, unique, final, uniform, input):
		self.preexisting = preexisting
		self.unique      = unique
		self.final       = final
		self.uniform     = uniform
		self.input       = input

class FieldAnnotation(Annotation):
	__slots__ = 'unique',

	def __init__(self, unique):
		self.unique = unique

emptyFieldAnnotation  = FieldAnnotation(False)
emptyObjectAnnotation = ObjectAnnotation(False, False, False, False, False)
