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
		b.append(Store(self, 'Array', collector.existing(-1), value))
		b.append(collector.returnNone())

		name = 'listappend'
		code = Code(name, selfp, [self, value], ['self', 'value'], None, None, retp, b)
		return code


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

		b.append(Assign(Load(self, 'LowLevel', collector.existing('parent')), parent))
		b.append(Assign(Load(parent, 'Array',collector.existing(-1)), value))
		b.append(Return(value))

		name = 'listiterator__next__'
		code = Code(name, selfp, [self], ['self'], None, None, retp, b)
		return code

	### xrange ###
	makeIterator('xrange__iter__', xrange, xtypes.XRangeIteratorType)
	attachAttrPtr(xtypes.XRangeIteratorType, 'next')(llast(simpleIteratorDescriptor(collector, 'xrangeiteratornext', ('self',), int)))
