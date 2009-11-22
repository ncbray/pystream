#@PydevCodeAnalysisIgnore

from __future__ import absolute_import

from stubs.stubcollector import stubgenerator

@stubgenerator
def makeFloat(collector):
	llfunc        = collector.llfunc
	export        = collector.export
	highLevelStub = collector.highLevelStub
	replaceObject = collector.replaceObject
	replaceAttr   = collector.replaceAttr
	fold          = collector.fold
	staticFold    = collector.staticFold
	attachPtr     = collector.attachPtr


	#############################
	### Primitive conversions ###
	#############################

	@staticFold(lambda i: float(i))
	@llfunc(primitive=True)
	def prim_int_to_float(i):
		return allocate(float)


	##################################
	### Primitive float operations ###
	##################################

	@export
	@staticFold(lambda a: +a)
	@llfunc(primitive=True)
	def prim_float_pos(a):
		return allocate(float)

	@export
	@staticFold(lambda a: -a)
	@llfunc(primitive=True)
	def prim_float_neg(a):
		return allocate(float)

	@export
	@staticFold(lambda a, b: a+b)
	@llfunc(primitive=True)
	def prim_float_add(a, b):
		return allocate(float)

	@export
	@staticFold(lambda a, b: a-b)
	@llfunc(primitive=True)
	def prim_float_sub(a, b):
		return allocate(float)

	@export
	@staticFold(lambda a, b: a*b)
	@llfunc(primitive=True)
	def prim_float_mul(a, b):
		return allocate(float)

	@export # HACK
	@staticFold(lambda a, b: a/b)
	@llfunc(primitive=True)
	def prim_float_div(a, b):
		return allocate(float)

	@staticFold(lambda a, b: a%b)
	@llfunc(primitive=True)
	def prim_float_mod(a, b):
		return allocate(float)

	@export # HACK
	@staticFold(lambda a, b: a**b)
	@llfunc(primitive=True)
	def prim_float_pow(a, b):
		return allocate(float)

	@staticFold(lambda a, b: a==b)
	@fold(lambda a, b: a==b)
	@llfunc(primitive=True)
	def prim_float_eq(a, b):
		return allocate(bool)

	@staticFold(lambda a, b: a!=b)
	@fold(lambda a, b: a!=b)
	@llfunc(primitive=True)
	def prim_float_ne(a, b):
		return allocate(bool)

	@staticFold(lambda a, b: a<b)
	@fold(lambda a, b: a<b)
	@llfunc(primitive=True)
	def prim_float_lt(a, b):
		return allocate(bool)

	@staticFold(lambda a, b: a<=b)
	@fold(lambda a, b: a<=b)
	@llfunc(primitive=True)
	def prim_float_le(a, b):
		return allocate(bool)

	@staticFold(lambda a, b: a>b)
	@fold(lambda a, b: a>b)
	@llfunc(primitive=True)
	def prim_float_gt(a, b):
		return allocate(bool)

	@staticFold(lambda a, b: a>=b)
	@fold(lambda a, b: a>=b)
	@llfunc(primitive=True)
	def prim_float_ge(a, b):
		return allocate(bool)


	##############################
	### Float object functions ###
	##############################

	@attachPtr(float, '__pos__')
	@llfunc
	def float__pos__(self):
		return prim_float_pos(self)

	@attachPtr(float, '__neg__')
	@llfunc
	def float__neg__(self):
		return prim_float_neg(self)

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

	@attachPtr(float, '__eq__')
	@llfunc
	def float__eq__(self, other):
		other = coerce_to_float(other)
		if isinstance(other, float):
			return prim_float_eq(self, other)
		else:
			return NotImplemented

	@attachPtr(float, '__ne__')
	@llfunc
	def float__ne__(self, other):
		other = coerce_to_float(other)
		if isinstance(other, float):
			return prim_float_ne(self, other)
		else:
			return NotImplemented

	@attachPtr(float, '__lt__')
	@llfunc
	def float__lt__(self, other):
		other = coerce_to_float(other)
		if isinstance(other, float):
			return prim_float_lt(self, other)
		else:
			return NotImplemented

	@attachPtr(float, '__le__')
	@llfunc
	def float__le__(self, other):
		other = coerce_to_float(other)
		if isinstance(other, float):
			return prim_float_le(self, other)
		else:
			return NotImplemented

	@attachPtr(float, '__gt__')
	@llfunc
	def float__gt__(self, other):
		other = coerce_to_float(other)
		if isinstance(other, float):
			return prim_float_gt(self, other)
		else:
			return NotImplemented

	@attachPtr(float, '__ge__')
	@llfunc
	def float__ge__(self, other):
		other = coerce_to_float(other)
		if isinstance(other, float):
			return prim_float_ge(self, other)
		else:
			return NotImplemented