from __future__ import absolute_import

from  programIR.python.ast import *

from . stubcollector import stubgenerator
from . llutil import simpleDescriptor
#, allocate, getType, call, returnNone, type_lookup, inst_lookup, loadAttribute
import types

import operator

def noself(code):
	code.selfparam = None
	return code

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
	attachPtr     = collector.attachPtr

	# TODO should call:
	# 	__nonzero__
	# 	__len__
	# 	True
	fold(bool)(export(llast(simpleDescriptor(collector, 'convertToBool', ('o',), bool, hasSelfParam=False))))
	fold(lambda o: not o)(export(llast(simpleDescriptor(collector, 'invertedConvertToBool', ('o',), bool, hasSelfParam=False))))

	# Horrible hack, as vargs depend on creating a tuple,
	# and creating a tuple depends on vargs.
	@export
	@descriptive
	@noself
	@llfunc
	def buildTuple(*vargs):
		return vargs

	# TODO accept arguments
	#export(llast(simpleDescriptor(collector, 'buildList', (), list, hasSelfParam=False)))
	#export(llast(simpleDescriptor(collector, 'buildMap', (), dict, hasSelfParam=False)))

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

		b.append(collector.loadAttribute(function, types.FunctionType, 'func_globals', globalDict))
		b.append(Assign(Check(globalDict, 'Dictionary', name), temp))


		t = Suite()
		t.append(Assign(Load(globalDict, 'Dictionary', name), result))

		f = Suite()
		f.append(Assign(Load(collector.existing(__builtins__), 'Dictionary', name), result))

		c = Condition(Suite(), temp)
		b.append(Switch(c, t, f))

		b.append(Return(result))

		fname = 'interpreterLoadGlobal'
		code = Code(fname, None, [function, name], ['function', 'name'], None, None, retp, b)
		return code


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
		b.append(collector.loadAttribute(function, types.FunctionType, 'func_globals', globalDict))
		b.append(Store(globalDict, 'Dictionary', name, value))
		b.append(collector.returnNone())

		fname = 'interpreterStoreGlobal'
		code = Code(fname, None, [function, name, value], ['function', 'name', 'value'], None, None, retp, b)
		return code

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
			b.append(Return(retval))

			code = Code(name, None, args, list(argnames), None, None, retp, b)
			return code

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
		f = export(llast(simpleAttrCall('interpreter%s' % op, op, ['self', 'other'])))

		# HACK?
		if op in ('__eq__', '__ne__', '__gt__', '__ge__', '__lt__', '__le__'):
			foldF = getattr(operator, op)
			if foldF:
				fold(foldF)(f)

	for op in opnames.inplace.itervalues():
		export(llast(simpleAttrCall('interpreter%s' % op, op, ['self', 'other'])))

	for op in opnames.unaryPrefixLUT.itervalues():
		export(llast(simpleAttrCall('interpreter%s' % op, op, ['self'])))



	##export(llast(simpleAttrCall('interpreteris', 'is', ['self', 'other'])))
	##export(llast(simpleAttrCall('interpreteris not', 'is not', ['self', 'other'])))
	##
	##export(llast(simpleAttrCall('interpreterin', 'in', ['self', 'other'])))
	##export(llast(simpleAttrCall('interpreternot in', 'not in', ['self', 'other'])))
