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
	def prim_float_add(a, b):
		return allocate(float)

	@descriptive
	@staticFold(lambda a, b: a-b)
	@llfunc
	def prim_float_sub(a, b):
		return allocate(float)

	@descriptive
	@staticFold(lambda a, b: a*b)
	@llfunc
	def prim_float_mul(a, b):
		return allocate(float)

	@descriptive
	@staticFold(lambda a, b: a/b)
	@llfunc
	def prim_float_div(a, b):
		return allocate(float)

	@descriptive
	@staticFold(lambda a, b: a%b)
	@llfunc
	def prim_float_mod(a, b):
		return allocate(float)

	@descriptive
	@staticFold(lambda a, b: a**b)
	@llfunc
	def prim_float_pow(a, b):
		return allocate(float)

	@descriptive
	@staticFold(lambda a, b: a==b)
	@llfunc
	def prim_float_eq(a, b):
		return allocate(bool)

	@descriptive
	@staticFold(lambda a, b: a!=b)
	@llfunc
	def prim_float_ne(a, b):
		return allocate(bool)

	@descriptive
	@staticFold(lambda a, b: a<b)
	@llfunc
	def prim_float_lt(a, b):
		return allocate(bool)

	@descriptive
	@staticFold(lambda a, b: a<=b)
	@llfunc
	def prim_float_le(a, b):
		return allocate(bool)

	@descriptive
	@staticFold(lambda a, b: a>b)
	@llfunc
	def prim_float_gt(a, b):
		return allocate(bool)

	@descriptive
	@staticFold(lambda a, b: a>=b)
	@llfunc
	def prim_float_ge(a, b):
		return allocate(bool)

	### Primitive integer ###

	@descriptive
	@staticFold(lambda a, b: a+b)
	@llfunc
	def prim_int_add(a, b):
		return allocate(int)

	@descriptive
	@staticFold(lambda a, b: a-b)
	@llfunc
	def prim_int_sub(a, b):
		return allocate(int)

	@descriptive
	@staticFold(lambda a, b: a*b)
	@llfunc
	def prim_int_mul(a, b):
		return allocate(int)

	@descriptive
	@staticFold(lambda a, b: a/b)
	@llfunc
	def prim_int_div(a, b):
		return allocate(int)

	@descriptive
	@staticFold(lambda a, b: a%b)
	@llfunc
	def prim_int_mod(a, b):
		return allocate(int)

	@descriptive
	@staticFold(lambda a, b: a**b)
	@llfunc
	def prim_int_pow(a, b):
		return allocate(int)

	@descriptive
	@staticFold(lambda a, b: a==b)
	@llfunc
	def prim_int_eq(a, b):
		return allocate(bool)

	@descriptive
	@staticFold(lambda a, b: a!=b)
	@llfunc
	def prim_int_ne(a, b):
		return allocate(bool)

	@descriptive
	@staticFold(lambda a, b: a<b)
	@llfunc
	def prim_int_lt(a, b):
		return allocate(bool)

	@descriptive
	@staticFold(lambda a, b: a<=b)
	@llfunc
	def prim_int_le(a, b):
		return allocate(bool)

	@descriptive
	@staticFold(lambda a, b: a>b)
	@llfunc
	def prim_int_gt(a, b):
		return allocate(bool)

	@descriptive
	@staticFold(lambda a, b: a>=b)
	@llfunc
	def prim_int_ge(a, b):
		return allocate(bool)


	### Float object functions ###

	# TODO longs?  booleans?
	@llfunc
	def coerce_to_float(value):
		if isinstance(value, int):
			return prim_int_to_float(value)
		else:
			return value

	@attachPtr(float, '__add__')
	@llfunc
	def float__add__(self, other):
		other = coerce_to_float(other)
		if isinstance(other, float):
			return prim_float_add(self, other)
		else:
			return NotImplemented

	@attachPtr(float, '__sub__')
	@llfunc
	def float__sub__(self, other):
		other = coerce_to_float(other)
		if isinstance(other, float):
			return prim_float_sub(self, other)
		else:
			return NotImplemented

	@attachPtr(float, '__mul__')
	@llfunc
	def float__mul__(self, other):
		other = coerce_to_float(other)
		if isinstance(other, float):
			return prim_float_mul(self, other)
		else:
			return NotImplemented

	@attachPtr(float, '__div__')
	@llfunc
	def float__div__(self, other):
		other = coerce_to_float(other)
		if isinstance(other, float):
			return prim_float_div(self, other)
		else:
			return NotImplemented

	@attachPtr(float, '__mod__')
	@llfunc
	def float__mod__(self, other):
		other = coerce_to_float(other)
		if isinstance(other, float):
			return prim_float_mod(self, other)
		else:
			return NotImplemented


	@attachPtr(float, '__pow__')
	@llfunc
	def float__pow__(self, other):
		other = coerce_to_float(other)
		if isinstance(other, float):
			return prim_float_pow(self, other)
		else:
			return NotImplemented

#	@attachPtr(float, '__eq__')
#	@llfunc
#	def float__eq__(self, other):
#		other = coerce_to_float(other)
#		if isinstance(other, float):
#			return prim_float_eq(self, other)
#		else:
#			return NotImplemented

#	@attachPtr(float, '__ne__')
#	@llfunc
#	def float__ne__(self, other):
#		other = coerce_to_float(other)
#		if isinstance(other, float):
#			return prim_float_ne(self, other)
#		else:
#			return NotImplemented

#	@attachPtr(float, '__lt__')
#	@llfunc
#	def float__lt__(self, other):
#		other = coerce_to_float(other)
#		if isinstance(other, float):
#			return prim_float_lt(self, other)
#		else:
#			return NotImplemented

#	@attachPtr(float, '__le__')
#	@llfunc
#	def float__le__(self, other):
#		other = coerce_to_float(other)
#		if isinstance(other, float):
#			return prim_float_le(self, other)
#		else:
#			return NotImplemented

#	@attachPtr(float, '__gt__')
#	@llfunc
#	def float__gt__(self, other):
#		other = coerce_to_float(other)
#		if isinstance(other, float):
#			return prim_float_gt(self, other)
#		else:
#			return NotImplemented

#	@attachPtr(float, '__ge__')
#	@llfunc
#	def float__ge__(self, other):
#		other = coerce_to_float(other)
#		if isinstance(other, float):
#			return prim_float_ge(self, other)
#		else:
#			return NotImplemented


	@attachPtr(int, '__add__')
	@llfunc
	def int__add__(self, other):
		if isinstance(other, int):
			return prim_int_add(self, other)
		elif isinstance(other, float):
			return prim_float_add(prim_int_to_float(self), other)
		else:
			return NotImplemented

	@attachPtr(int, '__sub__')
	@llfunc
	def int__sub__(self, other):
		if isinstance(other, int):
			return prim_int_sub(self, other)
		elif isinstance(other, float):
			return prim_float_sub(prim_int_to_float(self), other)
		else:
			return NotImplemented


	@attachPtr(int, '__mul__')
	@llfunc
	def int__mul__(self, other):
		if isinstance(other, int):
			return prim_int_mul(self, other)
		elif isinstance(other, float):
			return prim_float_mul(prim_int_to_float(self), other)
		else:
			return NotImplemented

	@attachPtr(int, '__div__')
	@llfunc
	def int__div__(self, other):
		if isinstance(other, int):
			return prim_int_div(self, other)
		elif isinstance(other, float):
			return prim_float_div(prim_int_to_float(self), other)
		else:
			return NotImplemented

	@attachPtr(int, '__mod__')
	@llfunc
	def int__mod__(self, other):
		if isinstance(other, int):
			return prim_int_mod(self, other)
		elif isinstance(other, float):
			return prim_float_mod(prim_int_to_float(self), other)
		else:
			return NotImplemented

	@attachPtr(int, '__pow__')
	@llfunc
	def int__pow__(self, other):
		if isinstance(other, int):
			return prim_int_pow(self, other)
		elif isinstance(other, float):
			return prim_float_pow(prim_int_to_float(self), other)
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