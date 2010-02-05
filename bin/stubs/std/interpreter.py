#@PydevCodeAnalysisIgnore

from __future__ import absolute_import

from  language.python import ast

from .. stubcollector import stubgenerator

import types
import operator

def noself(code):
	p = code.codeparameters
	code.codeparameters = ast.CodeParameters(None, p.params, p.paramnames, p.defaults, p.vparam, p.kparam, p.returnparams)
	return code

def compileFunction(s, name):
	g = None
	l = {}
	eval(compile(s, name, 'exec'), g, l)
	assert len(l) == 1
	return l.values()[0]

@stubgenerator
def makeInterpreterStubs(collector):
	attachAttrPtr = collector.attachAttrPtr
	llfunc        = collector.llfunc
	export        = collector.export
	replaceAttr   = collector.replaceAttr
	fold          = collector.fold
	staticFold    = collector.staticFold
	attachPtr     = collector.attachPtr

	# HACK for hand-op
	global func_globals_attr
	func_globals_attr = collector.compiler.slots.uniqueSlotName(types.FunctionType.__dict__['func_globals'])


	def interpfunc(f=None, descriptive=False):
		def wrapper(f):
			return export(noself(llfunc(f, descriptive=descriptive)))

		if f is not None:
			return wrapper(f)
		else:
			return wrapper


	# TODO should call:
	# 	__nonzero__
	# 	__len__
	# 	True
	@fold(bool)
	@interpfunc(descriptive=True)
	def convertToBool(o):
		return allocate(bool)

	@fold(lambda o: not o)
	@interpfunc(descriptive=True)
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


		template = """def %(name)s(%(args)s):
	clsDict = load(load(%(self)s, 'type'), 'dictionary')
	meth = loadDict(clsDict, %(attr)r)
	return meth(%(args)s)
""" % {'name':name, 'attr':attr, 'self':argnames[0], 'args':", ".join(argnames)}

		f = compileFunction(template, '<generated - %s>' % name)
		return interpfunc(f)

	def simpleBinaryOp(name, attr, rattr):
		assert isinstance(name, str), name
		assert isinstance(attr, str), attr
		assert isinstance(rattr, str), rattr


		template = """def %(name)s(self, other):
	result = NotImplemented

	clsDict = load(load(self, 'type'), 'dictionary')
	if checkDict(clsDict, %(attr)r):
		meth = loadDict(clsDict, %(attr)r)
		result = meth(self, other)

	if result is NotImplemented:
		clsDict = load(load(other, 'type'), 'dictionary')
		if checkDict(clsDict, %(rattr)r):
			meth = loadDict(clsDict, %(rattr)r)
			result = meth(other, self)

	return result
""" % {'name':name, 'attr':attr, 'rattr':rattr}

		f = compileFunction(template, '<generated - %s>' % name)
		return interpfunc(f)

	def simpleInplaceBinaryOp(name, iattr, attr, rattr):
		assert isinstance(name, str), name
		assert isinstance(iattr, str), iattr
		assert isinstance(attr, str), attr
		assert isinstance(rattr, str), rattr


		template = """def %(name)s(self, other):
	result = NotImplemented

	clsDict = load(load(self, 'type'), 'dictionary')
	if checkDict(clsDict, %(iattr)r):
		meth = loadDict(clsDict, %(iattr)r)
		result = meth(self, other)

	if result is NotImplemented:
		if checkDict(clsDict, %(attr)r):
			meth = loadDict(clsDict, %(attr)r)
			result = meth(self, other)

	if result is NotImplemented:
		clsDict = load(load(other, 'type'), 'dictionary')
		if checkDict(clsDict, %(rattr)r):
			meth = loadDict(clsDict, %(rattr)r)
			result = meth(other, self)

	return result
""" % {'name':name, 'iattr':iattr, 'attr':attr, 'rattr':rattr}

		f = compileFunction(template, '<generated - %s>' % name)
		return interpfunc(f)

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

	def dynamictuple(*args):
		for arg in args:
			if isinstance(arg, tuple): raise Exception
		return args

	# Horrible hack, as vargs depend on creating a tuple,
	# and creating a tuple depends on vargs.
	@staticFold(tuple)
	@fold(dynamictuple)
	@interpfunc(descriptive=True)
	def buildTuple(*vargs):
		return vargs

	@staticFold(tuple)
	@fold(dynamictuple)
	@interpfunc
	def interpreter_buildTuple0():
		inst = allocate(tuple)
		store(inst, 'length', 0)
		return inst

	@staticFold(tuple)
	@fold(dynamictuple)
	@interpfunc
	def interpreter_buildTuple1(arg0):
		inst = allocate(tuple)
		store(inst, 'length', 1)
		storeArray(inst, 0, arg0)
		return inst

	@staticFold(tuple)
	@fold(dynamictuple)
	@interpfunc
	def interpreter_buildTuple2(arg0, arg1):
		inst = allocate(tuple)
		store(inst, 'length', 2)
		storeArray(inst, 0, arg0)
		storeArray(inst, 1, arg1)
		return inst

	@staticFold(tuple)
	@fold(dynamictuple)
	@interpfunc
	def interpreter_buildTuple3(arg0, arg1, arg2):
		inst = allocate(tuple)
		store(inst, 'length', 3)
		storeArray(inst, 0, arg0)
		storeArray(inst, 1, arg1)
		storeArray(inst, 2, arg2)
		return inst

	@staticFold(tuple)
	@fold(dynamictuple)
	@interpfunc
	def interpreter_buildTuple4(arg0, arg1, arg2, arg3):
		inst = allocate(tuple)
		store(inst, 'length', 4)
		storeArray(inst, 0, arg0)
		storeArray(inst, 1, arg1)
		storeArray(inst, 2, arg2)
		storeArray(inst, 3, arg3)
		return inst

	@staticFold(tuple)
	@fold(dynamictuple)
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

	simpleAttrCall('interpreter_getitem', '__getitem__', ['self', 'key'])
	simpleAttrCall('interpreter_setitem', '__setitem__', ['self', 'key', 'value'])
	simpleAttrCall('interpreter_delitem', '__delitem__', ['self', 'key'])
	# in / not in / __contains__?
	simpleAttrCall('interpreter_iter', '__iter__', ['self'])
	simpleAttrCall('interpreter_next', 'next', ['self'])



	from util.python import opnames

	def declare(op, isCompare):
		name  = opnames.forward[op]
		rname = opnames.reverse[op]


		f = simpleBinaryOp('interpreter%s' % name, name, rname)
		foldF = getattr(operator, name)
		if foldF:
			staticFold(foldF)(f)
			if isCompare:
				fold(foldF)(f)

		if not isCompare:
			iname = opnames.inplace[op]
			i = simpleInplaceBinaryOp('interpreter%s' % iname, iname, name, rname)

	for op in opnames.opLUT.keys():
		declare(op, False)

	for op in opnames.compare.keys():
		declare(op, True)

	for op in opnames.unaryPrefixLUT.itervalues():
		f = simpleAttrCall('interpreter%s' % op, op, ['self'])
		foldF = getattr(operator, op)
		if foldF: staticFold(foldF)(f)


	# TODO is / is not / in / not in
