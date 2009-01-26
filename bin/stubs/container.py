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
		selfp = Local('internal_self')
		self = Local('self')
		temp = Local('temp')
		retp = Local('internal_return')

		# Locals
		inst = Local('inst')

		b = Suite()
		t = Existing(itertype)
		allocate(b, t, inst)
		b.append(Store(inst, 'LowLevel', Existing('parent'), self))

		t = Existing(int)
		allocate(b, t, temp) # HACK no init?
		b.append(Store(inst, 'LowLevel', Existing('iterCurrent'), temp))

		b.append(Return(inst))

		code = Code(name, selfp, [self], ['self'], None, None, retp, b)
		f = Function(name, code)
		descriptive(f)
		return f

	return makeIteratorWrap

def simpleIteratorDescriptor(name, argnames, rt, hasSelfParam=True):
	assert isinstance(name, str), name
	assert isinstance(argnames, (tuple, list)), argnames
	assert isinstance(rt, type), rt

	def simpleDescriptorBuilder():
		if hasSelfParam:
			selfp = Local('internal_self')
		else:
			selfp = None

		args  = [Local(argname) for argname in argnames]
		inst  = Local('inst')
		temp  = Local('temp')
		retp  = Local('internal_return')

		b = Suite()
		t = Existing(rt)
		allocate(b, t, inst)
		# HACK no init?

		b.append(Assign(Load(args[0], 'LowLevel', Existing('iterCurrent')), temp))
		b.append(Store(args[0], 'LowLevel', Existing('iterCurrent'), temp))

		# Return the allocated object
		b.append(Return(inst))

		code = Code(name, selfp, args, list(argnames), None, None, retp, b)
		f = Function(name, code)

		descriptive(f)

		return f

	return simpleDescriptorBuilder

### Tuple ###
makeIterator('tuple__iter__', tuple, xtypes.TupleIteratorType)


### List ###
@attachAttrPtr(list, 'append')
@descriptive
@llast
def listappend():

	# Param
	selfp = Local('internal_self')
	self = Local('self')
	retp = Local('internal_return')
	value = Local('value')

	b = Suite()
	b.append(Store(self, 'Array', Existing(-1), value))
	returnNone(b)

	name = 'listappend'
	code = Code(name, selfp, [self, value], ['self', 'value'], None, None, retp, b)
	f = Function(name, code)

	return f


makeIterator('list__iter__', list, xtypes.ListIteratorType)

@attachAttrPtr(xtypes.ListIteratorType, 'next')
@descriptive
@llast
def listiterator__next__():

	# Param
	selfp = Local('internal_self')
	self = Local('self')
	retp = Local('internal_return')


	parent = Local('parent')
	value = Local('value')

	b = Suite()

	b.append(Assign(Load(self, 'LowLevel',Existing('parent')), parent))
	b.append(Assign(Load(parent, 'Array', Existing(-1)), value))
	b.append(Return(value))

	name = 'listiterator__next__'
	code = Code(name, selfp, [self], ['self'], None, None, retp, b)
	f = Function(name, code)

	return f

### xrange ###
makeIterator('xrange__iter__', xrange, xtypes.XRangeIteratorType)
attachAttrPtr(xtypes.XRangeIteratorType, 'next')(llast(simpleIteratorDescriptor('xrangeiteratornext', ('self',), int)))
