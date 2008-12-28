from common import opnames

# Built operation -> attribute LUT
def buildOpLUT():
	# TODO __cmp__?
	opLUT = {'New':'__new__', 'Init':'__init__', 'Delete':'__del__',
		 'Call':'__call__',
		 'Repr':'__repr__', 'Str':'__str__', 'Unicode':'__unicode__',
		 'Hash':'__hash__', 'Nonzero':'__nonzero__',


		 'GetAttribute':'__getattribute__',
		 'GetAttr':'__getattr__', 'SetAttribute':'__setattr__', 'DelAttribute':'__delattr__',
		 
		 'GetProperty':'__get__', 'SetProperty':'__set__', 'DelProperty':'__delete__',
		 'Length':'__len__', 'GetSubscript':'__getitem__', 'SetSubscript':'__setitem__', 'DelSubscript':'__delitem__',
		 'GetIterator':'__iter__', 'GetNext':'next', 'Contains':'__contains__',
		 }

	for name in opnames.forward.itervalues():
		opLUT[name] = name

	for name in opnames.reverse.itervalues():
		opLUT[name] = name

	for name in opnames.inplace.itervalues():
		opLUT[name] = name

	for name in opnames.unaryPrefixLUT.itervalues():
		opLUT[name] = name

	return opLUT

opLUT = buildOpLUT()
