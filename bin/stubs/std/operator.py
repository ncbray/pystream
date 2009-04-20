from __future__ import absolute_import

# TODO remove once type__call__ and method__call__ are made into a functions.
from language.python.ast import *

# HACK for highlevel functions?
from util import xtypes
method  = xtypes.MethodType
function = xtypes.FunctionType

from .. stubcollector import stubgenerator

# HACK for manually created functions
from language.python.annotations import Origin

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

	### Primitive conversions ###
	@descriptive
	@staticFold(lambda i: float(i))
	@llfunc
	def prim_int_to_float(i):
		return allocate(float)

	### Primitive float ###
	@descriptive
	@staticFold(lambda a, b: a+b)
	@llfunc
	def prim_float_add_float(a, b):
		return allocate(float)

	@descriptive
	@staticFold(lambda a, b: a-b)
	@llfunc
	def prim_float_sub_float(a, b):
		return allocate(float)

	@descriptive
	@staticFold(lambda a, b: a*b)
	@llfunc
	def prim_float_mul_float(a, b):
		return allocate(float)

	@descriptive
	@staticFold(lambda a, b: a/b)
	@llfunc
	def prim_float_div_float(a, b):
		return allocate(float)

	@descriptive
	@staticFold(lambda a, b: a**b)
	@llfunc
	def prim_float_pow_float(a, b):
		return allocate(float)

	### Primitive integer ###

	@descriptive
	@staticFold(lambda a, b: a+b)
	@llfunc
	def prim_int_add_int(a, b):
		return allocate(int)

	@descriptive
	@staticFold(lambda a, b: a-b)
	@llfunc
	def prim_int_sub_int(a, b):
		return allocate(int)

	@descriptive
	@staticFold(lambda a, b: a*b)
	@llfunc
	def prim_int_mul_int(a, b):
		return allocate(int)

	@descriptive
	@staticFold(lambda a, b: a/b)
	@llfunc
	def prim_int_div_int(a, b):
		return allocate(int)


	@descriptive
	@staticFold(lambda a, b: a**b)
	@llfunc
	def prim_int_pow_int(a, b):
		return allocate(int)

	@attachPtr(float, '__add__')
	@llfunc
	def float__add__(self, other):
		if isinstance(other, float):
			return prim_float_add_float(self, other)
		elif isinstance(other, int):
			return prim_float_add_float(self, prim_int_to_float(other))
		else:
			return NotImplemented

	@attachPtr(float, '__sub__')
	@llfunc
	def float__add__(self, other):
		if isinstance(other, float):
			return prim_float_sub_float(self, other)
		elif isinstance(other, int):
			return prim_float_sub_float(self, prim_int_to_float(other))
		else:
			return NotImplemented

	@attachPtr(float, '__mul__')
	@llfunc
	def float__mul__(self, other):
		if isinstance(other, float):
			return prim_float_mul_float(self, other)
		elif isinstance(other, int):
			return prim_float_mul_float(self, prim_int_to_float(other))
		else:
			return NotImplemented

	@attachPtr(float, '__div__')
	@llfunc
	def float__div__(self, other):
		if isinstance(other, float):
			return prim_float_div_float(self, other)
		elif isinstance(other, int):
			return prim_float_div_float(self, prim_int_to_float(other))
		else:
			return NotImplemented

	@attachPtr(float, '__pow__')
	@llfunc
	def float__pow__(self, other):
		if isinstance(other, float):
			return prim_float_pow_float(self, other)
		elif isinstance(other, int):
			return prim_float_pow_float(self, prim_int_to_float(other))
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
				attachPtr(t, name)(dummyBinary)

		for name in opnames.unaryPrefixLUT.itervalues():
			if typehasattr(t, name):
				attachPtr(t, name)(dummyUnary)

	attachDummyNumerics(int,   int_binary_op,        dummyCompareOperation, dummyUnaryOperation)
	attachDummyNumerics(float, dummyBinaryOperation, dummyCompareOperation, dummyUnaryOperation)
	attachDummyNumerics(long,  dummyBinaryOperation, dummyCompareOperation, dummyUnaryOperation)
	attachDummyNumerics(str,   dummyBinaryOperation, dummyCompareOperation, dummyUnaryOperation)

	@export
	@descriptive
	@llfunc
	def int_rich_compare(self, other):
		return allocate(bool)