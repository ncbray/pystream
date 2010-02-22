#@PydevCodeAnalysisIgnore

from __future__ import absolute_import

from stubs.stubcollector import stubgenerator

@stubgenerator
def makeInteger(collector):
	llfunc        = collector.llfunc
	export        = collector.export
	replaceAttr   = collector.replaceAttr
	fold          = collector.fold
	staticFold    = collector.staticFold
	attachPtr     = collector.attachPtr


	####################################
	### Primitive integer operations ###
	####################################

	@export
	@staticFold(lambda a, b: a+b)
	@llfunc(primitive=True)
	def prim_int_add(a, b):
		return allocate(int)

	@export
	@staticFold(lambda a, b: a-b)
	@llfunc(primitive=True)
	def prim_int_sub(a, b):
		return allocate(int)

	@export
	@staticFold(lambda a, b: a*b)
	@llfunc(primitive=True)
	def prim_int_mul(a, b):
		return allocate(int)

	@export
	@staticFold(lambda a, b: a/b)
	@llfunc(primitive=True)
	def prim_int_div(a, b):
		return allocate(int)

	@export
	@staticFold(lambda a, b: a%b)
	@llfunc(primitive=True)
	def prim_int_mod(a, b):
		return allocate(int)

	@export
	@staticFold(lambda a, b: a**b)
	@llfunc(primitive=True)
	def prim_int_pow(a, b):
		return allocate(int)

	@export
	@staticFold(lambda a, b: a==b)
	@fold(lambda a, b: a==b)
	@llfunc(primitive=True)
	def prim_int_eq(a, b):
		return allocate(bool)

	@export
	@staticFold(lambda a, b: a!=b)
	@fold(lambda a, b: a!=b)
	@llfunc(primitive=True)
	def prim_int_ne(a, b):
		return allocate(bool)

	@export
	@staticFold(lambda a, b: a<b)
	@fold(lambda a, b: a<b)
	@llfunc(primitive=True)
	def prim_int_lt(a, b):
		return allocate(bool)

	@export
	@staticFold(lambda a, b: a<=b)
	@fold(lambda a, b: a<=b)
	@llfunc(primitive=True)
	def prim_int_le(a, b):
		return allocate(bool)

	@export
	@staticFold(lambda a, b: a>b)
	@fold(lambda a, b: a>b)
	@llfunc(primitive=True)
	def prim_int_gt(a, b):
		return allocate(bool)

	@export
	@staticFold(lambda a, b: a>=b)
	@fold(lambda a, b: a>=b)
	@llfunc(primitive=True)
	def prim_int_ge(a, b):
		return allocate(bool)


	################################
	### Integer object functions ###
	################################

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


	@replaceAttr(int, '__eq__')
	@llfunc
	def int__eq__(self, other):
		if isinstance(other, int):
			return prim_int_eq(self, other)
		elif isinstance(other, float):
			return prim_float_eq(prim_int_to_float(self), other)
		else:
			return NotImplemented

	@replaceAttr(int, '__ne__')
	@llfunc
	def int__ne__(self, other):
		if isinstance(other, int):
			return prim_int_ne(self, other)
		elif isinstance(other, float):
			return prim_float_ne(prim_int_to_float(self), other)
		else:
			return NotImplemented

	@replaceAttr(int, '__lt__')
	@llfunc
	def int__le__(self, other):
		if isinstance(other, int):
			return prim_int_lt(self, other)
		elif isinstance(other, float):
			return prim_float_lt(prim_int_to_float(self), other)
		else:
			return NotImplemented

	@replaceAttr(int, '__le__')
	@llfunc
	def int__le__(self, other):
		if isinstance(other, int):
			return prim_int_le(self, other)
		elif isinstance(other, float):
			return prim_float_le(prim_int_to_float(self), other)
		else:
			return NotImplemented


	@replaceAttr(int, '__gt__')
	@llfunc
	def int__lge__(self, other):
		if isinstance(other, int):
			return prim_int_gt(self, other)
		elif isinstance(other, float):
			return prim_float_gt(prim_int_to_float(self), other)
		else:
			return NotImplemented

	@replaceAttr(int, '__ge__')
	@llfunc
	def int__ge__(self, other):
		if isinstance(other, int):
			return prim_int_ge(self, other)
		elif isinstance(other, float):
			return prim_float_ge(prim_int_to_float(self), other)
		else:
			return NotImplemented
