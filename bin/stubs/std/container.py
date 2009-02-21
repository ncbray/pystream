from __future__ import absolute_import

from .. stubcollector import stubgenerator

from util import xtypes
tupleiterator  = xtypes.TupleIteratorType
listiterator   = xtypes.ListIteratorType
xrangeiterator = xtypes.XRangeIteratorType

@stubgenerator
def makeContainerStubs(collector):
	highLevelStub = collector.highLevelStub
	replaceObject = collector.replaceObject
	replaceAttr   = collector.replaceAttr

	llfunc        = collector.llfunc
	export        = collector.export
	fold          = collector.fold
	descriptive   = collector.descriptive
	attachPtr     = collector.attachPtr

	### Tuple ###
	@attachPtr(tuple, '__iter__')
	@descriptive
	@llfunc
	def tuple__iter__(self):
		iterator = allocate(tupleiterator)
		store(iterator, 'parent', self)
		store(iterator, 'iterCurrent', allocate(int))
		return iterator

	# TODO bounds check?
	@attachPtr(xtypes.TupleType, '__getitem__')
	@llfunc
	def tuple__getitem__(self, key):
		return loadArray(self, key)


	### List ###
	@attachPtr(list, '__getitem__')
	@descriptive
	@llfunc
	def list__getitem__(self, index):
		return loadArray(self, -1)

	@attachPtr(list, '__setitem__')
	@descriptive
	@llfunc
	def list__setitem__(self, index, value):
		storeArray(self, -1, value)

	@attachPtr(list, 'append')
	@descriptive
	@llfunc
	def list_append(self, value):
		storeArray(self, -1, value)

	@attachPtr(list, '__iter__')
	@descriptive
	@llfunc
	def list__iter__(self):
		iterator = allocate(listiterator)
		store(iterator, 'parent', self)
		store(iterator, 'iterCurrent', allocate(int))
		return iterator

	@attachPtr(xtypes.ListIteratorType, 'next')
	@descriptive
	@llfunc
	def listiterator_next(self):
		store(self, 'iterCurrent', load(self, 'iterCurrent'))
		return loadArray(load(self, 'parent'), -1)

	### xrange ###
	@attachPtr(xrange, '__iter__')
	@descriptive
	@llfunc
	def xrange__iter__(self):
		iterator = allocate(xrangeiterator)
		store(iterator, 'parent', self)
		store(iterator, 'iterCurrent', allocate(int))
		return iterator

	@attachPtr(xrangeiterator, 'next')
	@descriptive
	@llfunc
	def xrangeiterator_next(self):
		store(self, 'iterCurrent', load(self, 'iterCurrent'))
		return allocate(int)
