from __future__ import absolute_import

from  language.python.ast import *
from  language.python.annotations import Origin

from .. stubcollector import stubgenerator

import types
import operator
import util

def noself(code):
	code.selfparam = None
	return code

# HACK for hand-op
func_globals_attr = util.uniqueSlotName(types.FunctionType.__dict__['func_globals'])

@stubgenerator
def makeInterpreterStubs(collector):
	attachAttrPtr = collector.attachAttrPtr
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

	def interpfunc(f):
		return export(noself(llfunc(f)))

	# TODO should call:
	# 	__nonzero__
	# 	__len__
	# 	True
	@fold(bool)
	@descriptive
	@interpfunc
	def convertToBool(o):
		return allocate(bool)

	@fold(lambda o: not o)
	@descriptive
	@interpfunc
	def invertedConvertToBool(o):
		return allocate(bool)

	@interpfunc
	def interpreterLoadGlobal(function, name):
		# HACK Causes a problem for cloning?
		#globalDict = function.func_globals
		globalDict = loadAttr(function, func_globals_attr)

		if checkDict(globalDict, name):
			return loadDict(globalDict, name)
		else:
			return loadDict(__builtins__, name)

	@interpfunc
	def interpreterStoreGlobal(function, name, value):
		globalDict = function.func_globals
		storeDict(globalDict, name, value)


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

			b.append(collector.instLookup(args[0], attr, func))
			b.append(Assign(Call(func, args, [], None, None), [retval]))
			b.append(Return([retval]))

			code = Code(name, None, args, list(argnames), None, None, [retp], b)
			code.rewriteAnnotation(origin=Origin(name, __file__, 0))
			return code

		return simpleAttrCallBuilder

	@interpfunc
	def interpreter_getattribute(self, key):
		call = loadDict(load(load(self, 'type'), 'dictionary'), '__getattribute__')
		return call(self, key)

	@interpfunc
	def interpreter_setattr(self, key, value):
		call = loadDict(load(load(self, 'type'), 'dictionary'), '__setattr__')
		return call(self, key, value)

	# Note: must have internal self parameter.
	# TODO fallback paths that call this should shift the self param over,
	# instead of using internal_self?
	@export
	@llfunc
	def interpreter_call(*vargs):
		call = loadDict(load(load(internal_self, 'type'), 'dictionary'), '__call__')
		return call(internal_self, *vargs)

	# Horrible hack, as vargs depend on creating a tuple,
	# and creating a tuple depends on vargs.
	@descriptive
	@interpfunc
	def buildTuple(*vargs):
		return vargs

	@interpfunc
	def interpreter_buildTuple0():
		inst = allocate(tuple)
		store(inst, 'length', 0)
		return inst

	@interpfunc
	def interpreter_buildTuple1(arg0):
		inst = allocate(tuple)
		store(inst, 'length', 1)
		storeArray(inst, 0, arg0)
		return inst

	@interpfunc
	def interpreter_buildTuple2(arg0, arg1):
		inst = allocate(tuple)
		store(inst, 'length', 2)
		storeArray(inst, 0, arg0)
		storeArray(inst, 1, arg1)
		return inst

	@interpfunc
	def interpreter_buildTuple3(arg0, arg1, arg2):
		inst = allocate(tuple)
		store(inst, 'length', 3)
		storeArray(inst, 0, arg0)
		storeArray(inst, 1, arg1)
		storeArray(inst, 2, arg2)
		return inst

	@interpfunc
	def interpreter_buildTuple4(arg0, arg1, arg2, arg3):
		inst = allocate(tuple)
		store(inst, 'length', 4)
		storeArray(inst, 0, arg0)
		storeArray(inst, 1, arg1)
		storeArray(inst, 2, arg2)
		storeArray(inst, 3, arg3)
		return inst

	@interpfunc
	def interpreter_buildTuple5(arg0, arg1, arg2, arg3, arg4):
		inst = allocate(tuple)
		store(inst, 'length', 5)
		storeArray(inst, 0, arg0)
		storeArray(inst, 1, arg1)
		storeArray(inst, 2, arg2)
		storeArray(inst, 3, arg3)
		storeArray(inst, 4, arg4)
		return inst

	@interpfunc
	def interpreter_unpack1(arg):
		return arg[0]

	@interpfunc
	def interpreter_unpack2(arg):
		return arg[0], arg[1]

	@interpfunc
	def interpreter_unpack3(arg):
		return arg[0], arg[1], arg[2]

	@interpfunc
	def interpreter_unpack4(arg):
		return arg[0], arg[1], arg[2], arg[3]

	@interpfunc
	def interpreter_unpack5(arg):
		return arg[0], arg[1], arg[2], arg[3], arg[4]

	@interpfunc
	def interpreter_unpack6(arg):
		return arg[0], arg[1], arg[2], arg[3], arg[4], arg[5]

	export(llast(simpleAttrCall('interpreter_getitem', '__getitem__', ['self', 'key'])))
	export(llast(simpleAttrCall('interpreter_setitem', '__setitem__', ['self', 'key', 'value'])))
	export(llast(simpleAttrCall('interpreter_delitem', '__delitem__', ['self', 'key'])))
	# in / not in / __contains__?
	export(llast(simpleAttrCall('interpreter_iter', '__iter__', ['self'])))
	export(llast(simpleAttrCall('interpreter_next', 'next', ['self'])))



	from common import opnames

	for op in opnames.forward.itervalues():
		f = export(llast(simpleAttrCall('interpreter%s' % op, op, ['self', 'other'])))
		foldF = getattr(operator, op)
		if foldF: staticFold(foldF)(f)


		# HACK?
		if op in ('__eq__', '__ne__', '__gt__', '__ge__', '__lt__', '__le__'):
			if foldF: fold(foldF)(f)

	for op in opnames.inplace.itervalues():
		f = export(llast(simpleAttrCall('interpreter%s' % op, op, ['self', 'other'])))
		foldF = getattr(operator, op)
		if foldF: staticFold(foldF)(f)


	for op in opnames.unaryPrefixLUT.itervalues():
		f = export(llast(simpleAttrCall('interpreter%s' % op, op, ['self'])))
		foldF = getattr(operator, op)
		if foldF: staticFold(foldF)(f)


	# TODO is / is not / in / not in
