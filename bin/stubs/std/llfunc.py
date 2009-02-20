from __future__ import absolute_import

# TODO remove once type__call__ and method__call__ are made into a functions.
from programIR.python.ast import *

# HACK for highlevel functions?
from util import xtypes
method  = xtypes.MethodType
function = xtypes.FunctionType

from .. stubcollector import stubgenerator

@stubgenerator
def makeLLFunc(collector):
	descriptive   = collector.descriptive
	llast         = collector.llast
	llfunc        = collector.llfunc
	export        = collector.export
	highLevelStub = collector.highLevelStub
	replaceObject = collector.replaceObject
	replaceAttr   = collector.replaceAttr
	fold          = collector.fold
	attachPtr     = collector.attachPtr

	##############
	### Object ###
	##############

	@attachPtr(object, '__init__')
	@descriptive
	@llfunc
	def object__init__(self, *vargs):
		pass

	# TODO __getattr__ fallback?
	# Exported for the method finding optimization
	@export
	@attachPtr(object, '__getattribute__')
	@llfunc
	def object__getattribute__(self, field):
		selfType = load(self, 'type')
		typeDict = load(selfType, 'dictionary')

		getter = False
		setter = False
		exists = checkDict(typeDict, field)

		if exists:
			desc     = loadDict(typeDict, field)
			descDict = load(load(desc, 'type'), 'dictionary')
			getter   = checkDict(descDict, '__get__')
			setter   = checkDict(descDict, '__set__')

		# TODO support ShortCircutAnd?
		if getter:
			if setter:
				# It's a data descriptor
				return loadDict(descDict, '__get__')(desc, self, selfType)

		if checkDict(typeDict, '__dict__'):
			# TODO Get the self dictionary using the dictionary descriptor.
			# Requires get/set support
#			dictDesc     = loadDict(typeDict, '__dict__')
#			dictDescType = load(dictDesc, 'type')
#			dictDescDict = load(dictDescType, 'dictionary')
#			selfDict     = loadDict(dictDescDict, '__get__')(dictDesc, self, selfType)

			selfDict = load(self, 'dictionary')
			if checkDict(selfDict, field):
				# Field in instance dictionary
				return loadDict(selfDict, field)

		if getter:
			# It's a method descriptor
			return loadDict(descDict, '__get__')(desc, self, selfType)
		elif exists:
			# It's a class variable
			return desc

		# HACK not found?
		return desc


	@attachPtr(object, '__setattr__')
	@llfunc
	def object__setattr__(self, field, value):
		selfType     = load(self, 'type')
		selfTypeDict = load(selfType, 'dictionary')

		if checkDict(selfTypeDict, field):
			desc = loadDict(selfTypeDict, field)
			descTypeDict = load(load(desc, 'type'), 'dictionary')
			if checkDict(descTypeDict, '__set__'):
				loadDict(descTypeDict, '__set__')(desc, self, value)
				return
			elif check(self, 'dictionary'):
				storeDict(load(self, 'dictionary'), field, value)
				return
		elif check(self, 'dictionary'):
			# Duplicated to ensure the compiler sees it as mutually exclusive.
			storeDict(load(self, 'dictionary'), field, value)
			return

		# TODO exception



	############
	### Type ###
	############

	@attachPtr(object, '__new__')
	@llfunc
	def object__new__(cls, *vargs):
		return allocate(cls)

	# Ugly: directly uses internal_self parameter
	@attachPtr(type, '__call__')
	@llast
	def type__call__():
		# Parameters
		self = Local('self')
		vargs = Local('vargs')

		# Temporaries
		new_method = Local('new_method')
		inst = Local('inst')
		init = Local('init')

		retp = Local('internal_return')

		b = Suite()

		# Call __new__
		b.append(collector.typeLookup(self, '__new__', new_method))
		b.append(Assign(Call(new_method, [self], [], vargs, None), inst))

		# TODO Do the isinstance check?
		# Call __init__
		b.append(collector.operation('__init__', inst, [], vargs, None))

		# Return the allocated object
		b.append(Return(inst))

		# Function definition
		name ='type__call__'
		code = Code(name, self, [], [], vargs, None, retp, b)
		return code


	################
	### Function ###
	################

	# TODO create unbound methods if inst == None?
	# Replace object must be on outside?
	@export
	@replaceObject(xtypes.FunctionType.__get__)
	@highLevelStub
	def function__get__(self, inst, cls):
		return method(self, inst, cls)


	##############
	### Method ###
	##############

	@replaceAttr(xtypes.MethodType, '__init__')
	@highLevelStub
	def method__init__(self, func, inst, cls):
		self.im_func 	= func
		self.im_self 	= inst
		self.im_class 	= cls

	# The __call__ function for a bound method.
	# TODO unbound method?
	# High level, give or take argument uglyness.
	# Exported for method call optimization
	@export
	@attachPtr(xtypes.MethodType, '__call__')
	@llast
	def method__call__():
		self = Local('self')

		im_self = Local('im_self')
		im_func = Local('im_func')
		temp 	= Local('temp')
		retp = Local('internal_return')

		vargs = Local('vargs')

		b = Suite()
		b.append(collector.loadAttribute(self, xtypes.MethodType, 'im_self', im_self))
		b.append(collector.loadAttribute(self, xtypes.MethodType, 'im_func', im_func))

		b.append(Assign(Call(im_func, [im_self], [], vargs, None), temp))
		b.append(Return(temp))

		name = 'method__call__'
		code = Code(name, self, [], [], vargs, None, retp, b)
		return code


	# Getter for function, returns method.
	@export
	@attachPtr(xtypes.MethodDescriptorType, '__get__')
	@attachPtr(xtypes.WrapperDescriptorType, '__get__') # HACK?
	@llfunc
	def methoddescriptor__get__(self, inst, cls):
		return method(load(self, 'function'), inst, cls)


	#########################
	### Member Descriptor ###
	#########################

	# Used for a slot data getter.
	# Low level, gets slot attribute.
	@attachPtr(xtypes.MemberDescriptorType, '__get__')
	@llfunc
	def memberdescriptor__get__(self, inst, cls):
		return loadAttr(inst, load(self, 'slot'))

	# For data descriptors, __set__
	# Low level, involves slot manipulation.
	@attachPtr(xtypes.MemberDescriptorType, '__set__')
	@llfunc
	def memberdescriptor__set__(self, inst, value):
		storeAttr(inst, load(self, 'slot'), value)


	###########################
	### Property Descriptor ###
	###########################

	# TODO test?
	@attachPtr(property, '__get__')
	@descriptive # HACK for debugging.
	@llfunc
	def property__get__(self, inst, cls):
		return self.fget(self, inst)

	###############
	### Numeric ###
	###############

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
				if name in ('__eq__', '__ne__', '__lt__', '__le__', '__gt__', '__ge__'):
					attachPtr(t, name)(dummyCompare)
				else:
					attachPtr(t, name)(dummyBinary)

		for name in opnames.reverse.itervalues():
			if typehasattr(t, name):
				if name in ('__eq__', '__ne__', '__lt__', '__le__', '__gt__', '__ge__'):
					attachPtr(t, name)(dummyCompare)
				else:
					attachPtr(t, name)(dummyBinary)

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

	#############
	### Tuple ###
	#############

	@attachPtr(xtypes.TupleType, '__getitem__')
	@descriptive
	@llfunc
	def tuple__getitem__(self, key):
		return loadArray(self, key)

	#########################
	### Builtin functions ###
	#########################

	# TODO full implementation requires loop unrolling?
	@fold(issubclass)
	@attachPtr(issubclass)
	@descriptive
	@llfunc
	def issubclass_stub(cls, clsinfo):
		return allocate(bool)

	@attachPtr(isinstance)
	@llfunc
	def isinstance_stub(obj, classinfo):
		return issubclass(load(obj, 'type'), classinfo)


	# TODO multiarg?
	@fold(max)
	@attachPtr(max)
	@llfunc
	def max_stub(a, b):
		return b if a < b else a

	# TODO multiarg?
	@fold(min)
	@attachPtr(min)
	@llfunc
	def min_stub(a, b):
		return a if a < b else b


	@fold(chr)
	@attachPtr(chr)
	@descriptive
	@llfunc
	def chr_stub(i):
		return allocate(str)

	@fold(ord)
	@attachPtr(ord)
	@descriptive
	@llfunc
	def ord_stub(c):
		return allocate(int)

	@attachPtr(str, '__getitem__')
	@descriptive
	@llfunc
	def str__getitem__(self, index):
		return allocate(str)