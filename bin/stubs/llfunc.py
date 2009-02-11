from __future__ import absolute_import

from programIR.python.ast import *

# HACK for highlevel functions?
from util import xtypes
method = xtypes.MethodType
function = xtypes.FunctionType

from . stubcollector import stubgenerator
from . llutil import simpleDescriptor
#, allocate, getType, returnNone, call, operation, type_lookup, inst_lookup, loadAttribute


@stubgenerator
def makeLLFunc(collector):
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

	##############
	### Object ###
	##############

	@attachAttrPtr(object, '__init__')
	@descriptive
	@llast
	def object__init__():
		# Param
		selfp = Local('internal_self')
		self  = Local('self')
		vargs = Local('vargs')
		retp  = Local('internal_return')

		b = Suite()
		b.append(collector.returnNone())

		name = 'object__init__'
		code = Code(name, selfp, [self], ['self'], vargs, None, retp, b)
		return code

	# Exported for the method finding optimization
	@export
	@attachAttrPtr(object, '__getattribute__')
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

		if check(self, 'dictionary'):
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

	# TODO incomplete
	# set object__getattribute__
	@attachAttrPtr(object, '__setattr__')
	@llast
	def object__setattr__():
		selfp = Local('internal_self')
		self = Local('self')

		# Param
		field = Local('field')
		value = Local('value')
		retp  = Local('internal_return')

		# Locals
		cls     = Local('cls')
		clsDict = Local('clsDict')

		desc     = Local('desc')
		descCls  = Local('descCls')
		descDict = Local('descDict')
		setter   = Local('setter')

		descExists = Local('descExists')
		hasSetter  = Local('hasSetter')

		selfDict   = Local('selfDict')

		b = Suite()

		b.append(collector.getType(self, cls))
		b.append(Assign(Load(cls, 'LowLevel', collector.existing('dictionary')), clsDict))




		t = Suite([])
		t.append(Assign(Load(clsDict, 'Dictionary', field), desc))
		t.append(collector.getType(desc, descCls))
		t.append(Assign(Load(descCls, 'LowLevel', collector.existing('dictionary')), descDict))


		ts = Suite()
		ts.append(Assign(Load(descDict, 'Dictionary', collector.existing('__set__')),setter))
		ts.append(Discard(Call(setter, [desc, self, value], [], None, None)))
		ts.append(collector.returnNone())


		f = Suite([])
		f.append(Assign(Load(self, 'LowLevel', collector.existing('dictionary')), selfDict))
		f.append(Store(selfDict, 'Dictionary', field, value))
		f.append(collector.returnNone())

		conditional = Local('conditional')
		condSuite = Suite([])
		condSuite.append(Assign(Check(descDict, 'Dictionary', collector.existing('__set__')), hasSetter))
		cond = Condition(condSuite, hasSetter)
		t.append(Switch(cond, ts, f))


		f = Suite([])
		f.append(Assign(Load(self, 'LowLevel', collector.existing('dictionary')), selfDict))
		f.append(Store(selfDict, 'Dictionary', field, value))
		f.append(collector.returnNone())


		conditional = Local('conditional')
		condSuite = Suite([])
		condSuite.append(Assign(Check(clsDict, 'Dictionary', field), descExists))
		cond = Condition(condSuite, descExists)
		b.append(Switch(cond, t, f))

		b.append(collector.returnNone())


		name = 'object__setattr__'
		code = Code(name, selfp, [self, field, value], ['self', 'field', 'value'], None, None, retp, b)
		return code


	############
	### Type ###
	############

	@attachAttrPtr(object, '__new__')
	@llast
	def object__new__():
		# Args
		self = Local('self')
		type_ = Local('type')
		vargs = Local('vargs')

		retp = Local('internal_return')

		# Locals
		inst = Local('inst')

		b = Suite()
		b.append(collector.allocate(type_, inst))
		b.append(Return(inst))

		name = 'object__new__'
		code = Code(name, self, [type_], ['type'], vargs, None, retp, b)
		return code


	@attachAttrPtr(type, '__call__')
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

	## TODO create unbound methods if inst == None?
	# Replace object must be on outside?
	@export
	@replaceObject(xtypes.FunctionType.__get__)
	@highLevelStub
	def function__get__(self, inst, cls):
		return method(self, inst, cls)


	##############
	### Method ###
	##############

	#@export
	@replaceAttr(xtypes.MethodType, '__init__')
	@highLevelStub
	def method__init__(self, func, inst, cls):
		self.im_func 	= func
		self.im_self 	= inst
		self.im_class 	= cls

	# The __call__ function for a bound method.
	# TODO unbound method?
	# High level, give or take argument uglyness.
	@export
	@attachAttrPtr(xtypes.MethodType, '__call__')
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


	# Low level, requires hidden function.
	# Getter for function, returns method.
	@export
	@attachAttrPtr(xtypes.MethodDescriptorType, '__get__')
	@attachAttrPtr(xtypes.WrapperDescriptorType, '__get__') # HACK?
	@llast
	def methoddescriptor__get__():

		# Param
		selfp = Local('internal_self')
		self = Local('self')
		inst = Local('inst')
		cls = Local('cls')
		retp = Local('internal_return')

		# Locals
		func 	= Local('func')
		result 	= Local('result')

		b = Suite()
		b.append(Assign(Load(self, 'LowLevel', collector.existing('function')), func))
		b.append(Assign(Call(collector.existing(xtypes.MethodType), [func, inst, cls], [], None, None), result))
		b.append(Return(result))

		name = 'methoddescriptor__get__'
		code = Code(name, selfp, [self, inst, cls], ['self', 'inst', 'cls'], None, None, retp, b)
		return code


	#########################
	### Member Descriptor ###
	#########################

	# Used for a slot data getter.
	# Low level, gets slot attribute.
	@attachAttrPtr(xtypes.MemberDescriptorType, '__get__')
	@llast
	def memberdescriptor__get__():
		# Param
		selfp = Local('internal_self')
		self = Local('self')
		inst = Local('inst')
		cls = Local('cls')
		retp = Local('internal_return')

		# Locals
		slot = Local('slot')
		result = Local('result')

		b = Suite()
		b.append(Assign(Load(self, 'LowLevel', collector.existing('slot')), slot))
		b.append(Assign(Load(inst, 'Attribute', slot), result))
		b.append(Return(result))


		name = 'memberdescriptor__get__'
		code = Code(name, selfp, [self, inst, cls], ['self', 'inst', 'cls'], None, None, retp, b)
		return code

	# For data descriptors, __set__
	# Low level, involves slot manipulation.
	@attachAttrPtr(xtypes.MemberDescriptorType, '__set__')
	@llast
	def memberdescriptor__set__():
		# Self
		selfp = Local('internal_self')
		self = Local('self')

		# Param
		inst 	= Local('inst')
		value 	= Local('value')
		slot 	= Local('slot')
		retp    = Local('internal_return')

		# Instructions
		b = Suite()
		b.append(Assign(Load(self, 'LowLevel', collector.existing('slot')), slot))
		b.append(Store(inst, 'Attribute', slot, value))
		b.append(collector.returnNone())

		name = 'memberdescriptor__set__'
		code = Code(name, selfp, [self, inst, value], ['self', 'inst', 'value'], None, None, retp, b)
		return code


	###########################
	### Property Descriptor ###
	###########################

	# Low level, requires hidden function.
	# Getter for function, returns method.
	@attachAttrPtr(property, '__get__')
	@descriptive # HACK for debugging.
	@llast
	def property__get__():
		# Param
		selfp = Local('internal_self')
		self = Local('self')
		inst = Local('inst')
		cls = Local('cls')
		retp = Local('internal_return')

		# Locals
		func 	= Local('func')
		result 	= Local('result')

		b = Suite()

		b.append(collector.attributeCall(self, property, 'fget', [inst], [], None, None, result))
		b.append(Return(result))

		name = 'property__get__'
		code = Code(name, selfp, [self, inst, cls], ['self', 'inst', 'cls'], None, None, retp, b)
		return code


	###############
	### Numeric ###
	###############

	# A rough approximation for most binary and unary operations.
	# Descriptive stub, and a hack.
	#@export
	@descriptive
	@llast
	def dummyBinaryOperation():
		selfp = Local('internal_self')
		t = Local('type_')
		inst = Local('inst')
		retp = Local('internal_return')

		args = []
		args.append(Local('self'))
		args.append(Local('other'))

		b = Suite()
		b.append(collector.getType(args[0], t))
		b.append(collector.allocate(t, inst))
		# HACK no init?  Don't know what arguments to pass...

		# Return the allocated object
		b.append(Return(inst))

		name = 'dummyBinaryOperation'
		code = Code(name, selfp, args, ['self', 'other'], None, None, retp, b)
		return code

	@descriptive
	@llast
	def dummyCompareOperation():
		selfp = Local('internal_self')
		t = Local('type_')
		inst = Local('inst')
		retp = Local('internal_return')

		args = []
		args.append(Local('self'))
		args.append(Local('other'))

		b = Suite()
		b.append(collector.allocate(collector.existing(bool), inst))
		# HACK no init?  Don't know what arguments to pass...

		# Return the allocated object
		b.append(Return(inst))

		name = 'dummyCompareOperation'
		code = Code(name, selfp, args, ['self', 'other'], None, None, retp, b)
		return code

	@descriptive
	@llast
	def dummyUnaryOperation():
		selfp = Local('internal_self')
		t = Local('type_')
		inst = Local('inst')
		retp = Local('internal_return')

		args = []
		args.append(Local('self'))

		b = Suite()
		b.append(collector.getType(args[0], t))
		b.append(collector.allocate(t, inst))
		# HACK no init?  Don't know what arguments to pass...

		# Return the allocated object
		b.append(Return(inst))

		name = 'dummyUnaryOperation'
		code = Code(name, selfp, args, ['self'], None, None, retp, b)
		return code

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
	def attachDummyNumerics(t, dummyBinary, dummyCompare, dummyUnary):
		for name in opnames.forward.itervalues():
			if hasattr(t, name):
				if name in ('__eq__', '__ne__', '__lt__', '__le__', '__gt__', '__ge__'):
					attachAttrPtr(t, name)(dummyCompare)
				else:
					attachAttrPtr(t, name)(dummyBinary)

		for name in opnames.reverse.itervalues():
			if hasattr(t, name):
				if name in ('__eq__', '__ne__', '__lt__', '__le__', '__gt__', '__ge__'):
					attachAttrPtr(t, name)(dummyCompare)
				else:
					attachAttrPtr(t, name)(dummyBinary)

		for name in opnames.inplace.itervalues():
			if hasattr(t, name):
				attachAttrPtr(t, name)(dummyBinary)

		for name in opnames.unaryPrefixLUT.itervalues():
			if hasattr(t, name):
				attachAttrPtr(t, name)(dummyUnary)

	##	if hasattr(t, '__nonzero__'):
	##		nz = descriptive(llast(simpleDescriptor('%s__nonzero__' % t.__name__, (), bool)))
	##		attachAttrPtr(t, '__nonzero__')(nz)

	attachDummyNumerics(int,   int_binary_op, dummyCompareOperation, dummyUnaryOperation)
	attachDummyNumerics(float, dummyBinaryOperation, dummyCompareOperation, dummyUnaryOperation)
	attachDummyNumerics(long,  dummyBinaryOperation, dummyCompareOperation, dummyUnaryOperation)
	attachDummyNumerics(str,   dummyBinaryOperation, dummyCompareOperation, dummyUnaryOperation)

	int_rich_compare_stub = export(descriptive(llast(simpleDescriptor(collector, 'int_rich_compare', ('a',  'b'), bool))))


	#############
	### Tuple ###
	#############

	@attachAttrPtr(xtypes.TupleType, '__getitem__')
	@descriptive
	@llast
	def tuple__getitem__():
		# Self
		self = Local('internal_self')

		# Param
		inst 	= Local('self')
		key 	= Local('key')
		retp    = Local('internal_return')

		# Temporaries
		result  = Local('result')

		# Instructions
		b = Suite()
		b.append(Assign(Load(inst, 'Array', key), result))
		b.append(Return(result))

		name = 'tuple__getitem__'
		code = Code(name, self, [inst, key], ['self', 'key'], None, None, retp, b)
		return code

	#########################
	### Builtin functions ###
	#########################

	# Easiest as a descriptive stub.
	# Should be a implementation, for precision, however.

	issubclass_stub = fold(issubclass)(attachPtr(issubclass)(llast(simpleDescriptor(collector, 'issubclass', ('class',  'classinfo'), bool))))

	@attachPtr(isinstance)
	@llfunc
	def isinstance_stub(obj, classinfo):
		return issubclass(load(obj, 'type'), classinfo)

	# HACK nothing like what max and min actually do.
	max_stub = fold(max)(attachPtr(max)(descriptive(llast(simpleDescriptor(collector, 'max', ('a',  'b'), float)))))
	min_stub = fold(min)(attachPtr(min)(descriptive(llast(simpleDescriptor(collector, 'min', ('a',  'b'), float)))))

	chr_stub = fold(chr)(attachPtr(chr)(descriptive(llast(simpleDescriptor(collector, 'chr', ('i',), str)))))
	ord_stub = fold(ord)(attachPtr(ord)(descriptive(llast(simpleDescriptor(collector, 'ord', ('c',), int)))))


	# String funcitons
	str_getitem_stub = attachAttrPtr(str, '__getitem__')(descriptive(llast(simpleDescriptor(collector, 'str__getitem__', ('self', 'index',), str))))
