from __future__ import absolute_import

from stubs.stubcollector import stubgenerator

@stubgenerator
def makeOperator(collector):
	descriptive   = collector.descriptive
	llast         = collector.llast
	llfunc        = collector.llfunc
	export        = collector.export
	highLevelStub = collector.highLevelStub
	replaceObject = collector.replaceObject
	replaceAttr   = collector.replaceAttr
	fold          = collector.fold
	staticFold    = collector.staticFold
	attachPtr     = collector.attachPtr


	# A rough approximation for most binary and unary operations.
	# Descriptive stub, and a hack.
	@descriptive
	@llfunc
	def dummyBinaryOperation(self, other):
		selfType = load(self, 'type')
		return allocate(selfType)

	@descriptive
	@llfunc
	def dummyCompareOperation(self, other):
		return allocate(bool)

	@descriptive
	@llfunc
	def dummyUnaryOperation(self):
		selfType = load(self, 'type')
		return allocate(selfType)

	@descriptive
	@llfunc
	def int_binary_op(self, other):
		if isinstance(other, int):
			return allocate(int)
		elif isinstance(other, float):
			return allocate(float)
		else:
			return NotImplemented


	from common import opnames
	def typehasattr(t, name):
		return name in t.__dict__

	def attachDummyNumerics(t, dummyBinary, dummyCompare, dummyUnary):
		for name in opnames.forward.itervalues():
			if typehasattr(t, name):
				try:
					if name in ('__eq__', '__ne__', '__lt__', '__le__', '__gt__', '__ge__'):
						attachPtr(t, name)(dummyCompare)
					else:
						attachPtr(t, name)(dummyBinary)
				except:
					pass

		for name in opnames.reverse.itervalues():
			if typehasattr(t, name):
				try:
					if name in ('__eq__', '__ne__', '__lt__', '__le__', '__gt__', '__ge__'):
						attachPtr(t, name)(dummyCompare)
					else:
						attachPtr(t, name)(dummyBinary)
				except:
					pass

		for name in opnames.inplace.itervalues():
			if typehasattr(t, name):
				try:
					attachPtr(t, name)(dummyBinary)
				except:
					pass

		for name in opnames.unaryPrefixLUT.itervalues():
			if typehasattr(t, name):
				try:
					attachPtr(t, name)(dummyUnary)
				except:
					pass

	attachDummyNumerics(int,   int_binary_op,        dummyCompareOperation, dummyUnaryOperation)
	attachDummyNumerics(float, dummyBinaryOperation, dummyCompareOperation, dummyUnaryOperation)
	attachDummyNumerics(long,  dummyBinaryOperation, dummyCompareOperation, dummyUnaryOperation)
	attachDummyNumerics(str,   dummyBinaryOperation, dummyCompareOperation, dummyUnaryOperation)

	@export
	@descriptive
	@llfunc
	def int_rich_compare(self, other):
		return allocate(bool)