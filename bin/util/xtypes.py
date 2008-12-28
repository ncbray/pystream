from types import *

# Extended "types"
# Includes some important types not available elsewhere.

# A descriptor that produces builtin methods.
MethodDescriptorType = type(str.__dict__['count'])

# Wraps a slot in a type opbject.
WrapperDescriptorType = type(str.__dict__['__add__'])


TupleIteratorType 	= type(iter(()))
ListIteratorType 	= type(iter([]))
XRangeIteratorType 	= type(iter(xrange(1)))


TypeNeedsStub = (MethodDescriptorType, WrapperDescriptorType, BuiltinFunctionType)
TypeNeedsHiddenStub = (MethodDescriptorType, WrapperDescriptorType)


ConstantTypes = set((str, int, float, long, NoneType, bool, CodeType))
