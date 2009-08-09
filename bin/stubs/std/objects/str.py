from __future__ import absolute_import

from stubs.stubcollector import stubgenerator
import operator

@stubgenerator
def makeString(collector):
	llast         = collector.llast
	llfunc        = collector.llfunc
	export        = collector.export
	highLevelStub = collector.highLevelStub
	replaceObject = collector.replaceObject
	replaceAttr   = collector.replaceAttr
	fold          = collector.fold
	staticFold    = collector.staticFold
	attachPtr     = collector.attachPtr


	################################
	### Primitive str operations ###
	################################

	@staticFold(lambda a, b: a+b)
	@llfunc(primitive=True)
	def prim_str_add(a, b):
		return allocate(str)

	@staticFold(lambda a, b: a*b)
	@llfunc(primitive=True)
	def prim_str_mul(a, b):
		return allocate(str)

	@staticFold(lambda a, b: a%b)
	@llfunc(primitive=True)
	def prim_str_mod(a, b):
		return allocate(str)

	@staticFold(lambda a, b: a==b)
	@fold(lambda a, b: a==b)
	@llfunc(primitive=True)
	def prim_str_eq(a, b):
		return allocate(bool)

	@staticFold(lambda a, b: a!=b)
	@fold(lambda a, b: a!=b)
	@llfunc(primitive=True)
	def prim_str_ne(a, b):
		return allocate(bool)

	@staticFold(lambda a, b: a<b)
	@fold(lambda a, b: a<b)
	@llfunc(primitive=True)
	def prim_str_lt(a, b):
		return allocate(bool)

	@staticFold(lambda a, b: a<=b)
	@fold(lambda a, b: a<=b)
	@llfunc(primitive=True)
	def prim_str_le(a, b):
		return allocate(bool)

	@staticFold(lambda a, b: a>b)
	@fold(lambda a, b: a>b)
	@llfunc(primitive=True)
	def prim_str_gt(a, b):
		return allocate(bool)

	@staticFold(lambda a, b: a>=b)
	@fold(lambda a, b: a>=b)
	@llfunc(primitive=True)
	def prim_str_ge(a, b):
		return allocate(bool)

	##############################
	### String object functions ###
	##############################

	@attachPtr(str, '__add__')
	@llfunc
	def str__add__(self, other):
		if isinstance(other, str):
			return prim_str_add(self, other)
		else:
			return NotImplemented

	# TODO support longs?
	@attachPtr(str, '__mul__')
	@llfunc
	def str__mul__(self, other):
		if isinstance(other, int):
			return prim_str_mul(self, other)
		else:
			return NotImplemented

	@attachPtr(str, '__mod__')
	@llfunc
	def str__mod__(self, other):
		if isinstance(other, str):
			return prim_str_mod(self, other)
		elif isinstance(other, tuple):
			return prim_str_mod(self, other)
		else:
			return NotImplemented

	@attachPtr(str, '__eq__')
	@llfunc
	def str__eq__(self, other):
		if isinstance(other, str):
			return prim_str_eq(self, other)
		else:
			return NotImplemented

	@attachPtr(str, '__ne__')
	@llfunc
	def str__ne__(self, other):
		if isinstance(other, str):
			return prim_str_ne(self, other)
		else:
			return NotImplemented

	@attachPtr(str, '__lt__')
	@llfunc
	def str__lt__(self, other):
		if isinstance(other, str):
			return prim_str_lt(self, other)
		else:
			return NotImplemented

	@attachPtr(str, '__le__')
	@llfunc
	def str__le__(self, other):
		if isinstance(other, str):
			return prim_str_le(self, other)
		else:
			return NotImplemented

	@attachPtr(str, '__gt__')
	@llfunc
	def str__gt__(self, other):
		if isinstance(other, str):
			return prim_str_gt(self, other)
		else:
			return NotImplemented

	@attachPtr(str, '__ge__')
	@llfunc
	def str__ge__(self, other):
		if isinstance(other, str):
			return prim_str_ge(self, other)
		else:
			return NotImplemented



	##############################
	### Other string functions ###
	##############################

	@staticFold(chr)
	@fold(chr)
	@attachPtr(chr)
	@llfunc(descriptive=True)
	def chr_stub(i):
		return allocate(str)

	@staticFold(ord)
	@fold(ord)
	@attachPtr(ord)
	@llfunc(descriptive=True)
	def ord_stub(c):
		return allocate(int)

	@attachPtr(str, '__getitem__')
	@staticFold(operator.getitem)
	@fold(operator.getitem)
	@llfunc(descriptive=True)
	def str__getitem__(self, index):
		return allocate(str)