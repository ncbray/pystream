from __future__ import absolute_import

from  programIR.python.ast import *

from . stubcollector import llast, attachAttrPtr, highLevelStub, export, fold, descriptive
from . llutil import simpleDescriptor, allocate, getType, call, returnNone, type_lookup, inst_lookup

# TODO should call:
# 	__nonzero__
# 	__len__
# 	True
fold(bool)(export(llast(simpleDescriptor('convertToBool', ('o',), bool, hasSelfParam=False))))


# BUG recursive definition.  Needs HasAttr instead.
##@fold(bool)
##@export
###@descriptive
##@llast
##def convertToBool():
##	# Param
##	self = Local('self')
##	field = Local('field')
##
##	# Locals
##	cls 	= Local('cls')
##	meth 	= Local('meth')
##
##	result = Local('result')
##
##	b = Suite()
##
##	# Load the attribute from the class
##	getType(b, self, cls)
##	b.append(Assign(Load(cls, 'Attribute', Existing('__nonzero__')), meth))
##
##
##	t = Suite([])
##	f = Suite([])
##
##	# Descriptor
##	call(t, meth, [self], None, None, result)
##
##	# No descriptor
##	f.append(Assign(Existing(True), result))
##
##
##	conditional = Local('conditional')
##	cond = Condition(Suite([Assign(ConvertToBool(meth), conditional)]), conditional)
##	b.append(Switch(cond, t, f))
##
##	b.append(Return(result))
##
##
##	code = Code(None, ['o'], [self, field], None, None, b)
##	f = Function('convertToBool', code)
##
##	return f


# A low-level stub (directly manipulates array slots)
# Horrible hack, as vargs depend on creating a tuple,
# and creating a tuple depends on vargs.
@export
@llast
def buildTuple():
	# Self
	#self = Local('self')
	vargs = Local('vargs')

	# Param
	n = []
	a = []

	# Temporaries
	retp    = Local('internal_return')

	# Instructions
	b = Suite()
	b.append(Return(vargs))

	name = 'buildTuple'
	code = Code(name, None, a, n, vargs, None, retp, b)
	f = Function(name, code)
	return f

### A low-level stub (multiple return values?)
### Abstract (no iteration)
##@export
##@llast
##def unpackSequence():
##	# Self
##	self = Local('self')
##
##	# Param
##	inst 	= Local('inst')
##
##	# Temporaries
##	temps = [Local('t%d'%i) for i in range(8)]
##
##
##	# Instructions
##	b = Suite()
##	for i in range(8):
##		b.append(Assign(temps[i], Load(inst, 'Array', Existing(i))))
##
##	b.append(Return(temps))
##
##	sig = FunctionSignature(self, ['inst'], [inst], [], None, None)
##
##	f = Function('unpackSequence', sig, b)
##
##	return f

# TODO accept arguments
export(llast(simpleDescriptor('buildList', (), list, hasSelfParam=False)))
export(llast(simpleDescriptor('buildMap', (), dict, hasSelfParam=False)))


@export
@llast
def interpreterLoadGlobal():
	# Param
	function, name = Local('function'), Local('name')

	# Temporaries
	globalDict = Local('globalDict')
	temp 	= Local('temp')
	result 	= Local('result')
	retp    = Local('internal_return')

	# Instructions
	b = Suite()
	b.append(Assign(Load(function, 'Attribute', Existing('func_globals')), globalDict))
	b.append(Assign(Check(globalDict, 'Dictionary', name), temp))


	t = Suite()
	t.append(Assign(Load(globalDict, 'Dictionary', name), result))

	f = Suite()
	f.append(Assign(Load(Existing(__builtins__), 'Dictionary', name), result))

	c = Condition(Suite(), temp)
	b.append(Switch(c, t, f))

	b.append(Return(result))

	fname = 'interpreterLoadGlobal'
	code = Code(fname, None, [function, name], ['function', 'name'], None, None, retp, b)
	f = Function(fname, code)

	return f


@export
@llast
def interpreterStoreGlobal():
	# Param
	function, name, value = Local('function'), Local('name'), Local('value')
	args = [function, name, value]

	# Temporaries
	globalDict = Local('globalDict')
	retp    = Local('internal_return')

	# Instructions
	b = Suite()
	b.append(Assign(Load(function, 'Attribute', Existing('func_globals')), globalDict))
	b.append(Store(globalDict, 'Dictionary', name, value))
	returnNone(b)

	fname = 'interpreterStoreGlobal'
	code = Code(fname, None, [function, name, value], ['function', 'name', 'value'], None, None, retp, b)
	f = Function(fname, code)

	return f

def simpleAttrCall(name, attr, argnames):
	assert isinstance(name, str), name
	assert isinstance(attr, str), attr
	assert isinstance(argnames, (tuple, list)), argnames

	def simpleAttrCallBuilder():
		# Param
		args = [Local(argname) for argname in argnames]



		# Temporaries
		attrtemp = Local('attrtemp')
		type_ 	= Local('type_')
		func 	= Local('func')
		retval 	= Local('retval')
		retp    = Local('internal_return')

		# Instructions
		b = Suite()

		inst_lookup(b, args[0], Existing(attr), func)
		call(b, func, args, None, None, retval)
		b.append(Return(retval))

		code = Code(name, None, args, list(argnames), None, None, retp, b)
		f = Function(name, code)
		return f

	return simpleAttrCallBuilder


export(llast(simpleAttrCall('interpreter_getattribute', '__getattribute__', ['self', 'key'])))
export(llast(simpleAttrCall('interpreter_setattr', '__setattr__', ['self', 'key', 'value'])))


export(llast(simpleAttrCall('interpreter_getitem', '__getitem__', ['self', 'key'])))
export(llast(simpleAttrCall('interpreter_setitem', '__setitem__', ['self', 'key', 'value'])))
export(llast(simpleAttrCall('interpreter_delitem', '__delitem__', ['self', 'key'])))
# in / not in / __contains__?
export(llast(simpleAttrCall('interpreter_iter', '__iter__', ['self'])))
export(llast(simpleAttrCall('interpreter_next', 'next', ['self'])))



from common import opnames

for op in opnames.forward.itervalues():
	export(llast(simpleAttrCall('interpreter%s' % op, op, ['self', 'other'])))

for op in opnames.inplace.itervalues():
	export(llast(simpleAttrCall('interpreter%s' % op, op, ['self', 'other'])))

for op in opnames.unaryPrefixLUT.itervalues():
	export(llast(simpleAttrCall('interpreter%s' % op, op, ['self'])))



##export(llast(simpleAttrCall('interpreteris', 'is', ['self', 'other'])))
##export(llast(simpleAttrCall('interpreteris not', 'is not', ['self', 'other'])))
##
##export(llast(simpleAttrCall('interpreterin', 'in', ['self', 'other'])))
##export(llast(simpleAttrCall('interpreternot in', 'not in', ['self', 'other'])))
