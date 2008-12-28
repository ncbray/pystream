from __future__ import absolute_import

from programIR.python.ast import *

# HACK for highlevel functions?
from util import xtypes
method = xtypes.MethodType
function = xtypes.FunctionType

from . stubcollector import llast, descriptive, attachPtr, attachAttrPtr, highLevelStub, replaceObject, replaceAttr, export, fold
from . llutil import simpleDescriptor, allocate, getType, returnNone, call, operation, type_lookup, inst_lookup

	
##############
### Object ###
##############

# Low level?

# types all have __get__ and __set__, set to null if not specified

# Indiredtion to dictionary is tricky, so is "hasattr(self, 'dictionary')"
#	Solve by assuming type specializtion?
#		Requires that low-level "hasattr"s are all specialized or transformed into type tests?

# "field in d" is impossible to resolve precisely unless:
#	"defined/undefined" analysis is used
#	Post-analysis information is used to bound the possible keys in a dictionary.
#		Post-analysis/cloning folding?


# Translating decompiled functions:
#	need to link globals (getattr/type) to the calls.  requires a bit of simple analysis.
#		effectively an op-based def-use?
# A great opprotunity to discover correlation and optimize?


##def object__getattribute__(self, field):
##	cls = type(self)
##
##	desc = type_lookup(cls, field)
##	# None vs. wrapped None?
##
##	f = desc.__get__
##	
##	if f:
##		s = desc.__set__
##		if s:
##			# Data descriptor
##			return f(cls, self)
##
##	if hasattr(self, 'dictionary'): # lowlevel
##		d = self.dictionary
##		if field in d:
##			# Contained in object dictionary
##			return d[field]
##
##	if f:
##		# Method descriptor
##		return f(cls, self)
##	elif desc:
##		# Not actually a descriptor, and nothing in the dictionary.
##		# Return class variable.
##		# Note: for this to work, we need to be able to distinguish between
##		# the class variable being None and the type lookup failing.
##		return desc
##	else:
##		# Assumes f exists, as exceptions are not supported.
##		# Returning "NotImplemented" simply provides a tracer for us to see if something goes wrong.
##		# Probabally should create a special purpose tracer.
##		#raise AttributeError, "'%.50s' object has no attribute '%.400s'" % (cls.__name__, field)
##		return NotImplemented
	

##def type_lookup(cls, field):
##	# HACK, possible due to flattened classes
##	# Assumes no possibility of error
##	return getattr(cls, field)


# HasAttr opcode
# dict.__contains__(self, key) -> bool
# dict.__get

def object__getattribute__(self, field):
	cls = type(self)
	cls = self.type

	#desc = type_lookup(cls, field)
	desc = getattr(cls, field)

	#if desc is not null:
	if True:
		f = getattr(desc, '__get__')
		if f:
			s = getattr(desc, '__set__')
			if s:
				# Data descriptor
				return f(cls, self)

	if hasattr(self, 'dictionary'): # lowlevel
		d = self.dictionary
		if field in d:
			# Contained in object dictionary
			return getdict(d, field)

##	if desc is not null:
	if True:
		if f:
			# Method descriptor
			return f(cls, self)
		else:
			# Not actually a descriptor, and nothing in the dictionary.
			# Return class variable.
			# Note: for this to work, we need to be able to distinguish between
			# the class variable being None and the type lookup failing.
			return desc
	else:
		# Assumes f exists, as exceptions are not supported.
		# Returning "NotImplemented" simply provides a tracer for us to see if something goes wrong.
		# Probabally should create a special purpose tracer.
		#raise AttributeError, "'%.50s' object has no attribute '%.400s'" % (cls.__name__, field)
		return NotImplemented
	

##@attachAttrPtr(object, '__getattribute__')
##@descriptive
##@llast
##def object__getattribute__():
##	# Param
##	self = Local('self')	
##	field = Local('field')
##
##	# Locals
##	cls 	= Local('cls')
##	desc 	= Local('desc')
##	d 	= Local('dict')
##
##	result = Local('result')
##
##	b = Suite()
##
##	# Load the attribute from the class
##	getType(b, self, cls)
##	b.append(Assign(Load(cls, 'Attribute', field), desc))
##
##
##	# TODO only call GetProperty on objects that support the descriptor protocall?
##	# Or should every object nominally support the protocall? o.__get__(inst, cls) -> o
##	operation(b, '__get__', desc, [self, cls], None, None, result)
##
##	# HACK flow insensitive.
##	b.append(Assign(Load(self, 'LowLevel', Existing('dictionary')), d))
##	b.append(Assign(Load(d, 'Dictionary', field), result))
##	b.append(Return(result))
##
##	code = Code(None, ['self', 'field'], [self, field], None, None, b)
##	f = Function('object__getattribute__', code)
##
##	return f



@export
@attachAttrPtr(object, '__getattribute__')
@descriptive   # HACK should work in most cases.
@llast
def object__getattribute__():
	# Param
	self = Local('self')	
	field = Local('field')

	# Locals
	cls 	= Local('cls')
	desc 	= Local('desc')

	result = Local('result')

	retp   = Local('internal_return')

	b = Suite()

	getType(b, self, cls)
	type_lookup(b, cls, field, desc)


	t = Suite([])

	# Get the descriptor
	descFunc = Local('descFunc')
	inst_lookup(t, desc, Existing('__get__'), descFunc)

	# Call the descriptor
	call(t, descFunc, [desc, self, cls], None, None, result)



	f = Suite([])
	
	# No descriptor
	d = Local('dict')
	f.append(Assign(Load(self, 'LowLevel', Existing('dictionary')), d))
	f.append(Assign(Load(d, 'Dictionary', field), result))


	conditional = Local('conditional')
	condSuite = Suite([])
	#condSuite.append(Assign(ConvertToBool(desc), conditional))
	allocate(condSuite, Existing(bool), conditional)
	cond = Condition(condSuite, conditional)

	b.append(Switch(cond, t, f))
	b.append(Return(result))


	code = Code(None, [self, field], ['self', 'field'], None, None, retp, b)
	f = Function('object__getattribute__', code)

	return f

##def isDataDescriptor(desc):
##	return hasattr(desc, '__get__') and hasattr(desc, '__set__')
##
##def object__getattribute__(self, field):
##	# data descriptor > dictionary > method descriptor > class attribute > error
##
##	cls = type(self)
##	desc = cls.lookup(field)
##	
##	if desc and isDataDescriptor(desc):
##		return desc.__get__(self, cls)
##	elif self.__dict__ and field in self.__dict__:
##		return self.__dict__[field]
##	elif desc and hasattr(desc, '__get__'):
##		return desc.__get__(self, cls)
##	elif desc:
##		return desc
##	else:
## 		raise AttributeError, "'%.50s' object has no attribute '%.400s'" % (cls.__name__, field)
	
@export
@highLevelStub
def default__get__(self, inst, cls):
	return self

# Default __setattr__
# Low level, requires class lookup?
@attachAttrPtr(object, '__setattr__')
@descriptive
@llast
def object__setattr__():
	self = Local('self')

	# Param
	field = Local('field')
	value = Local('value')
	retp  = Local('internal_return')

	# Locals
	#cls = Local('cls')
	desc = Local('desc')
	setter = Local('setter')

	b = Suite()

	inst_lookup(b, self, field, desc)
	inst_lookup(b, desc, Existing('__set__'), setter)
	call(b, setter, [desc, self, value], None, None)

	returnNone(b)

	code = Code(None, [self, field, value], ['self', 'field', 'value'], None, None, retp, b)
	f = Function('object__setattr__', code)

	return f	

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
	allocate(b, type_, inst)
	b.append(Return(inst))

	code = Code(self, [type_], ['type'], vargs, None, retp, b)
	f = Function('object__new__', code)
	return f


# Does not exist, hardwired in interpreter?
##@attachAttrPtr(object, '__nonzero__')
##@llast
##def object__nonzero__():
##	# Args
##	self = Local('self')
##
##	b = Suite()
##	b.append(Return(Existing(True)))
##
##	code = Code(self, [], [], None, None, b)
##	f = Function('object__nonzero__', code)
##	return f

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
	type_lookup(b, self, Existing('__new__'), new_method)		    
	call(b, new_method, [self], vargs, None, inst)

	# TODO Do the isinstance check?
	# Call __init__
	operation(b, '__init__', inst, [], vargs, None)

	# Return the allocated object
	b.append(Return(inst))

	# Function definition
	code = Code(self, [], [], vargs, None, retp, b)
	f = Function('type__call__', code)
	return f

##def type__call__(cls, *args, **kargs):
##	# TODO arg matching behavior?
##	# No override to new or init - no args
##	# Override new or init - args must match overriden
##	# Override both - just call both with given arguments?
##	
##	inst = cls.__new__(*args, **kargs)
##
##	if type(inst) == cls:
##		# TODO get __init__ from class via lookup...
##		inst.__init__(*args, **kargs)
##
##	return inst


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
	b.append(Assign(Load(self, 'Attribute', Existing('im_self')), im_self))
	b.append(Assign(Load(self, 'Attribute', Existing('im_func')), im_func))

	call(b, im_func, [im_self], vargs, None, temp)
	b.append(Return(temp))

	code = Code(self, [], [], vargs, None, retp, b)
	f = Function('method__call__', code)

	return f

### TODO what can be done about the ugly argument passing?  Will the analysis figure it out?
##@replaceObject(xtypes.MethodType.__get__)
##@highLevelStub
##def method__call__(self, *args, **kargs):
##	self.im_func(self.im_self, *args, **kargs)


# Low level, requires hidden function.
# Getter for function, returns method.
@export
@attachAttrPtr(xtypes.MethodDescriptorType, '__get__')
@attachAttrPtr(xtypes.WrapperDescriptorType, '__get__') # HACK?
@llast
def methoddescriptor__get__():

	# Param
	self = Local('self')
	inst = Local('inst')
	cls = Local('cls')
	retp = Local('internal_return')

	# Locals
	func 	= Local('func')
	result 	= Local('result')

	b = Suite()
	b.append(Assign(Load(self, 'LowLevel', Existing('function')), func))
	call(b, Existing(xtypes.MethodType), [func, inst, cls], None, None, result)
	b.append(Return(result))


	code = Code(None, [self, inst, cls], ['self', 'inst', 'cls'], None, None, retp, b)
	func = Function('methoddescriptor__get__', code)

	return func

#########################
### Member Descriptor ###
#########################

# Used for a slot data getter.
# Low level, gets slot attribute.
@attachAttrPtr(xtypes.MemberDescriptorType, '__get__')
@llast
def memberdescriptor__get__():
	# Param
	self = Local('self')
	inst = Local('inst')
	cls = Local('cls')
	retp = Local('internal_return')

	# Locals
	slot = Local('slot')
	result = Local('result')

	b = Suite()
	b.append(Assign(Load(self, 'LowLevel', Existing('slot')), slot))	
	b.append(Assign(Load(inst, 'Attribute', slot), result))
	b.append(Return(result))


	code = Code(None, [self, inst, cls], ['self', 'inst', 'cls'], None, None, retp, b)
	f = Function('memberdescriptor__get__', code)
	return f

# For data descriptors, __set__
# Low level, involves slot manipulation.
@attachAttrPtr(xtypes.MemberDescriptorType, '__set__')
@llast
def memberdescriptor__set__():
	# Self
	self = Local('self')

	# Param
	inst 	= Local('inst')
	value 	= Local('value')
	slot 	= Local('slot')
	retp    = Local('internal_return')

	# Instructions
	b = Suite()
	b.append(Assign(Load(self, 'LowLevel', Existing('slot')), slot))
	b.append(Discard(Store(inst, 'Attribute', slot, value)))
	returnNone(b)

	code = Code(None, [self, inst, value], ['self', 'inst', 'value'], None, None, retp, b)
	f = Function('memberdescriptor__set__', code)

	return f

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
	self = Local('self')
	inst = Local('inst')
	cls = Local('cls')
	retp = Local('internal_return')

	# Locals
	func 	= Local('func')
	result 	= Local('result')

	b = Suite()
	b.append(Assign(Load(self, 'Attribute', Existing('fget')), func))
	call(b, func, [inst], None, None, result)
	b.append(Return(result))

	code = Code(None, [self, inst, cls], ['self', 'inst', 'cls'], None, None, retp, b)
	func = Function('property__get__', code)

	return func

###############
### Numeric ###
###############

# A rough approximation for most binary and unary operations.
# Descriptive stub, and a hack.
#@export
@descriptive
@llast
def dummyBinaryOperation():
	t = Local('type_')
	inst = Local('inst')
	retp = Local('internal_return')

	args = []
	args.append(Local('self'))
	args.append(Local('other'))

	b = Suite()
	getType(b, args[0], t)
	allocate(b, t, inst)
	# HACK no init?  Don't know what arguments to pass...

	# Return the allocated object
	b.append(Return(inst))

	code = Code(None, args, ['self', 'other'], None, None, retp, b)
	f = Function('dummyBinaryOperation', code)

	return f


@descriptive
@llast
def dummyUnaryOperation():
	t = Local('type_')
	inst = Local('inst')
	retp = Local('internal_return')

	args = []
	args.append(Local('self'))

	b = Suite()
	getType(b, args[0], t)
	allocate(b, t, inst)
	# HACK no init?  Don't know what arguments to pass...

	# Return the allocated object
	b.append(Return(inst))

	code = Code(None, args, ['self'], None, None, retp, b)
	f = Function('dummyUnaryOperation', code)

	return f

from common import opnames
def attachDummyNumerics(t, dummyBinary, dummyUnary):
	for name in opnames.forward.itervalues():
		if hasattr(t, name):
			attachAttrPtr(t, name)(dummyBinary)

	for name in opnames.reverse.itervalues():
		if hasattr(t, name):
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

attachDummyNumerics(int,   dummyBinaryOperation, dummyUnaryOperation)
attachDummyNumerics(float, dummyBinaryOperation, dummyUnaryOperation)
attachDummyNumerics(long,  dummyBinaryOperation, dummyUnaryOperation)
attachDummyNumerics(str,   dummyBinaryOperation, dummyUnaryOperation)

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

	code = Code(self, [inst, key], ['self', 'key'], None, None, retp, b)
	f = Function('tuple__getitem__', code)
	return f

#########################
### Builtin functions ###
#########################

# Easiest as a descriptive stub.
# Should be a implementation, for precision, however.


# HACK should just hijack pointer.
# This would require decompiling a high-level function, however.
# Decompiling is ugly, as the decompiler depends on the stub functions.
##@replaceObject(isinstance)
##@highLevelStub
##def isinstance_stub(object, classinfo):
##	return issubclass(type(object), classinfo)

issubclass_stub = fold(issubclass)(attachPtr(issubclass)(llast(simpleDescriptor('issubclass', ('class',  'classinfo'), bool))))

@attachPtr(isinstance)
@llast
def isinstance_stub():
	# Self
	self = Local('internal_self')
	retp = Local('internal_return')

	# Param
	obj 	   = Local('object')
	classinfo  = Local('classinfo')

	# Temporaries
	type_   = Local('type_')
	result  = Local('result')

	# Instructions
	b = Suite()	
	getType(b, obj, type_)
	b.append(Assign(DirectCall(issubclass_stub, None, [type_, classinfo], [], None, None), result))
	b.append(Return(result))

	code = Code(self, [obj, classinfo], ['object', 'classinfo'], None, None, retp, b)
	f = Function('isinstance', code)
	return f


# HACK nothing like what max and min actually do.
max_stub = fold(max)(attachPtr(max)(descriptive(llast(simpleDescriptor('max', ('a',  'b'), float)))))
min_stub = fold(min)(attachPtr(min)(descriptive(llast(simpleDescriptor('min', ('a',  'b'), float)))))
