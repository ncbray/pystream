from __future__ import absolute_import

from  language.python.ast import *

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

	# Horrible hack, as vargs depend on creating a tuple,
	# and creating a tuple depends on vargs.
	@descriptive
	@interpfunc
	def buildTuple(*vargs):
		return vargs

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
			b.append(Assign(Call(func, args, [], None, None), retval))
			b.append(Return([retval]))

			code = Code(name, None, args, list(argnames), None, None, [retp], b)
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
