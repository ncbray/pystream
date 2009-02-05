from __future__ import absolute_import

import programIR.python.ast as ast

from . stubcollector import descriptive
import util

def allocate(b, t, inst):
	b.append(ast.Assign(ast.Allocate(t), inst))

	# Done automatically.
	#b.append(ast.Discard(ast.Store(inst, 'LowLevel', ast.Existing('type'), t)))

def getType(b, inst, result):
	b.append(ast.Assign(ast.Load(inst, 'LowLevel', ast.Existing('type')), result))

def returnNone(b):
	b.append(ast.Return(ast.Existing(None)))

def operation(b, attr, expr, args, vargs, kargs, result=None):
	type_ 	= ast.Local('type%s' % attr)
	func 	= ast.Local('func%s' % attr)

	inst_lookup(b, expr, ast.Existing(attr), func)

	newargs = [expr]
	newargs.extend(args)
	call(b, func, newargs, vargs, kargs, result)

def call(b, expr, args, vargs, kargs, result=None):
	# Make sure the optimizer doesn't get rid of the call attribute?
	#type_ 	= ast.Local('type__call__')
	#getType(b, expr, type_)
	#b.append(ast.Discard(ast.Load(type_, 'Attribute', ast.Existing('__call__'))))

	call = ast.Call(expr, args, [], vargs, kargs)

	if result != None:
		b.append(ast.Assign(call, result))
	else:
		b.append(ast.Discard(call))


def type_lookup(b, cls, field, result):
	clsDict 	= ast.Local('clsDict')
	b.append(ast.Assign(ast.Load(cls, 'LowLevel', ast.Existing('dictionary')), clsDict))
	b.append(ast.Assign(ast.Load(clsDict, 'Dictionary', field), result))


def inst_lookup(b, expr, field, result):
	cls = ast.Local('cls')
	getType(b, expr, cls)
	type_lookup(b, cls, field, result)


def loadAttribute(expr, type, name):
	descriptor  = type.__dict__[name]
	mangledName = util.uniqueSlotName(descriptor)
	return ast.Load(expr, 'Attribute', ast.Existing(mangledName))

def simpleDescriptor(name, argnames, rt, hasSelfParam=True):
	assert isinstance(name, str), name
	assert isinstance(argnames, (tuple, list)), argnames
	assert isinstance(rt, type), rt

	def simpleDescriptorBuilder():
		if hasSelfParam:
			selfp = ast.Local('internal_self')
		else:
			selfp = None

		args  = [ast.Local(argname) for argname in argnames]
		inst  = ast.Local('inst')
		retp  = ast.Local('internal_return')

		b = ast.Suite()
		t = ast.Existing(rt)
		allocate(b, t, inst)
		# HACK no init?

		# Return the allocated object
		b.append(ast.Return(inst))

		code = ast.Code(name, selfp, args, list(argnames), None, None, retp, b)
		f = ast.Function(name, code)

		descriptive(f)

		return f

	return simpleDescriptorBuilder

