from __future__ import absolute_import

from  programIR.python.ast import *

from . stubcollector import stubgenerator
#from . llutil import allocate, getType, returnNone
from util import xtypes


@stubgenerator
def makeContainerStubs(collector):
	attachAttrPtr = collector.attachAttrPtr
	descriptive   = collector.descriptive
	llast         = collector.llast
	llfunc        = collector.llfunc
	export        = collector.export
	highLevelStub = collector.highLevelStub
	replaceObject = collector.replaceObject
	replaceAttr   = collector.replaceAttr
	fold          = collector.fold
	attachPtr     = collector.attachPtr


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
			b.append(collector.allocate(collector.existing(itertype), inst))
			b.append(Store(inst, 'LowLevel', collector.existing('parent'), self))

			b.append(collector.allocate(collector.existing(int), temp)) # HACK no init?
			b.append(Store(inst, 'LowLevel', collector.existing('iterCurrent'), temp))

			b.append(Return(inst))

			code = Code(name, selfp, [self], ['self'], None, None, retp, b)
			descriptive(code)
			return code

		return makeIteratorWrap

	def simpleIteratorDescriptor(collector, name, argnames, rt, hasSelfParam=True):
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
			t = collector.existing(rt)
			b.append(collector.allocate(t, inst))
			# HACK no init?

			b.append(Assign(Load(args[0], 'LowLevel', collector.existing('iterCurrent')), temp))
			b.append(Store(args[0], 'LowLevel', collector.existing('iterCurrent'), temp))

			# Return the allocated object
			b.append(Return(inst))

			code = Code(name, selfp, args, list(argnames), None, None, retp, b)
			collector.descriptive(code)
			return code

		return simpleDescriptorBuilder

	### Tuple ###
	makeIterator('tuple__iter__', tuple, xtypes.TupleIteratorType)


	### List ###
	@attachAttrPtr(list, '__getitem__')
	@descriptive
	@llfunc
	def list__getitem__(self, index):
		return loadArray(self, -1)

	@attachAttrPtr(list, '__setitem__')
	@descriptive
	@llfunc
	def list__setitem__(self, index, value):
		storeArray(self, -1, value)

	@attachAttrPtr(list, 'append')
	@descriptive
	@llfunc
	def list_append(self, value):
		storeArray(self, -1, value)

	makeIterator('list__iter__', list, xtypes.ListIteratorType)

	@attachAttrPtr(xtypes.ListIteratorType, 'next')
	@descriptive
	@llfunc
	def listiterator__next__(self):
		return loadArray(load(self, 'parent'), -1)

	### xrange ###
	makeIterator('xrange__iter__', xrange, xtypes.XRangeIteratorType)
	attachAttrPtr(xtypes.XRangeIteratorType, 'next')(llast(simpleIteratorDescriptor(collector, 'xrangeiteratornext', ('self',), int)))
