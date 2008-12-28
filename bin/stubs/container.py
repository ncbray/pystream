from __future__ import absolute_import

from  programIR.python.ast import *

from . stubcollector import llast, descriptive, attachAttrPtr, highLevelStub, replaceAttr
from . llutil import simpleDescriptor, allocate, getType, returnNone


from util import xtypes

# Function for generating iterators.
def makeIterator(name, basetype, itertype):

	@attachAttrPtr(basetype, '__iter__')
	@llast
	def makeIteratorWrap():
		# Param
		self = Local('self')
		retp = Local('internal_return')

		# Locals
		inst = Local('inst')

		b = Suite()
		t = Existing(itertype)
		allocate(b, t, inst)
		b.append(Discard(Store(inst, 'LowLevel', Existing('parent'), self)))
		b.append(Return(inst))

		code = Code(None, [self], ['self'], None, None, retp, b)
		f = Function(name, code)
		descriptive(f)
		return f

	return makeIteratorWrap

### Tuple ###
makeIterator('tuple__iter__', tuple, xtypes.TupleIteratorType)


### List ###
@attachAttrPtr(list, 'append')
@descriptive
@llast
def listappend():

	# Param
	self = Local('self')
	retp = Local('internal_return')
	value = Local('value')

	b = Suite()
	b.append(Discard(Store(self, 'Array', Existing(-1), value)))
	returnNone(b)

	code = Code(None, [self, value], ['self', 'value'], None, None, retp, b)

		
	f = Function('listappend', code)

	return f


makeIterator('list__iter__', list, xtypes.ListIteratorType)

@attachAttrPtr(xtypes.ListIteratorType, 'next')
@descriptive
@llast
def listiterator__next__():

	# Param
	self = Local('self')
	retp = Local('internal_return')

	
	parent = Local('parent')
	value = Local('value')

	b = Suite()

	b.append(Assign(Load(self, 'LowLevel',Existing('parent')), parent))
	b.append(Assign(Load(parent, 'Array', Existing(-1)), value))
	b.append(Return(value))

	code = Code(None, [self], ['self'], None, None, retp, b)		
	f = Function('listiterator__next__', code)

	return f

#@replaceAttr(xrange, '__init__')
##def object__init__(self, *args):
##	return None


### xrange ###
@attachAttrPtr(object, '__init__')
@descriptive
@llast
def object__init__():
	# Param
	self = Local('self')
	vargs = Local('vargs')
	retp = Local('internal_return')

	b = Suite()
	returnNone(b)
	code = Code(None, [self], ['self'], vargs, None, retp, b)
		
	f = Function('object__init__', code)
	return f

makeIterator('xrange__iter__', xrange, xtypes.XRangeIteratorType)
attachAttrPtr(xtypes.XRangeIteratorType, 'next')(llast(simpleDescriptor('xrangeiteratornext', ('self',), int)))
