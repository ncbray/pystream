from __future__ import absolute_import

from _pystream import cfuncptr
from util import xtypes
from language.python import ast

import util

from . import lltranslator

class StubCollector(object):
	def __init__(self, compiler):
		self.compiler = compiler

		# HACK
		self.compiler.extractor.nameLUT = {}

		self.exports = {}

		self.highLevelGlobals 	= {'method':xtypes.MethodType}
		self.highLevelLUT 	= {}

		self.codeToFunction = {}

	##############################
	### AST building utilities ###
	##############################

	def existing(self, obj):
		return ast.Existing(self.compiler.extractor.getObject(obj))

	def allocate(self, t, target):
		return ast.Assign(ast.Allocate(t), [target])

	def getType(self, inst, result):
		return ast.Assign(ast.Load(inst, 'LowLevel', self.existing('type')), [result])

	def loadAttribute(self, expr, type, name, target):
		descriptor  = type.__dict__[name]
		mangledName = util.uniqueSlotName(descriptor)
		return ast.Assign(ast.Load(expr, 'Attribute', self.existing(mangledName)), [target])

	def returnNone(self):
		return ast.Return(self.existing(None))

	def typeLookup(self, cls, field, result):
		clsDict = ast.Local('clsDict')
		return [
			ast.Assign(ast.Load(cls, 'LowLevel', self.existing('dictionary')), [clsDict]),
			ast.Assign(ast.Load(clsDict, 'Dictionary', self.existing(field)), [result]),
			]

	def instLookup(self, expr, field, result):
		cls = ast.Local('cls')
		return [self.getType(expr, cls), self.typeLookup(cls, field, result)]

	def operation(self, attr, expr, args, vargs, kargs, result=None):
		type_ 	= ast.Local('type%s' % attr)
		func 	= ast.Local('func%s' % attr)

		newargs = [expr]
		newargs.extend(args)

		if result:
			return [
				self.instLookup(expr, attr, func),
				ast.Assign(ast.Call(func, newargs, [], vargs, kargs), [result])
				]
		else:
			return [
				self.instLookup(expr, attr, func),
				ast.Discard(ast.Call(func, newargs, [], vargs, kargs))
				]

	def attributeCall(self, expr, type, field, args, kwds, vargs, kargs, result=None):
		method = ast.Local('method_%s' % field)
		getter = self.loadAttribute(expr, type, field, method)
		call   = ast.Call(method, args, kwds, vargs, kargs)
		if result:
			callStmt = ast.Assign(call, [result])
		else:
			callStmt = ast.Discard(call)
		return [getter, callStmt]

	#####################
	### Stub building ###
	#####################

	def export(self, funcast):
		if isinstance(funcast, xtypes.FunctionType):
			name = funcast.func_name
		else:
			name = funcast.name

		assert not name in self.exports
		self.exports[name] = funcast
		return funcast

	def registerFunction(self, func, code):
		extractor = self.compiler.extractor
		extractor.desc.functions.append(code)
		extractor.nameLUT[code.name] = func

		if func:
			extractor.replaceCode(func, code)
			self.codeToFunction[code] = func

	def llast(self, f):
		code = f()
		assert code.isCode(), type(code)
		self.registerFunction(None, code)
		self.compiler.extractor.desc.functions.append(code)
		return code

	def llfunc(self, func=None, descriptive=False, primitive=False):
		def wrapper(func):
			code = self.compiler.extractor.decompileFunction(func, descriptive=(primitive or descriptive))
			self.registerFunction(func, code)

			if primitive:
				code = self.primitive(code)
			elif descriptive:
				code = self.descriptive(code)

			code = lltranslator.translate(self.compiler, func, code)

			return code

		if func is not None:
			return wrapper(func)
		else:
			return wrapper

	def cfuncptr(self, obj):
		try:
			return cfuncptr(obj)
		except TypeError:
			raise TypeError, "Cannot get pointer from %r" % type(obj)

	############################
	### Attachment functions ###
	############################

	def attachAttrPtr(self, t, attr):
		assert isinstance(t, type), t
		assert isinstance(attr, str), attr

		meth = getattr(t, attr)
		ptr = self.cfuncptr(meth)

		def callback(code):
			assert code.isCode(), type(code)
			self.compiler.extractor.attachStubToPtr(code, ptr)
			return code
		return callback


	def attachPtr(self, pyobj, attr=None):
		original = pyobj
		if attr is not None:
			d = pyobj.__dict__
			assert attr in d, (pyobj, attr)
			pyobj = pyobj.__dict__[attr]

		ptr = self.cfuncptr(pyobj)

		def callback(code):
			assert code.isCode(), type(code)
			extractor = self.compiler.extractor

			extractor.attachStubToPtr(code, ptr)

			# Check the binding.
			obj  = extractor.getObject(pyobj)
			call = extractor.getCall(obj)

			if code is not call:
				print extractor.pointerToObject
				print extractor.pointerToStub

			assert code is call, (original, pyobj, code, call)

			return code

		return callback

	def fold(self, func):
		def callback(code):
			assert code.isCode(), type(code)
			code.rewriteAnnotation(staticFold=func, dynamicFold=func)
			return code
		return callback

	def staticFold(self, func):
		def callback(code):
			assert code.isCode(), type(code)
			code.rewriteAnnotation(staticFold=func)
			return code
		return callback

	def descriptive(self,code):
		assert code.isCode(), type(code)
		code.rewriteAnnotation(descriptive=True)
		return code

	def primitive(self,code):
		assert code.isCode(), type(code)
		code.rewriteAnnotation(descriptive=True, primitive=True)
		return code

	##################
	### High Level ###
	##################

	def highLevelStub(self, f):
		# Let the function use the common global dictionary.
		# Recreate the function with different globals.
		f = util.replaceGlobals(f, self.highLevelGlobals)

		# Register
		self.highLevelLUT[f.func_name] = f

		# Add to the common global dictionary
		self.highLevelGlobals[f.func_name] = f

		return f

	### Attachment functions ###
	def replaceObject(self, o):
		def callback(f):
			assert self.highLevelLUT[f.func_name] == f, "Must declare as high level stub before replacing."
			self.compiler.extractor.replaceObject(o, f)
			return f
		return callback

	def replaceAttr(self, o, attr):
		def callback(obj):
			if not isinstance(obj, xtypes.FunctionType):
				assert obj.isCode(), type(obj)
				f = self.codeToFunction[obj]
			else:
				f = obj
				assert self.highLevelLUT[f.func_name] == f, "Must declare as high level stub before replacing."
			self.compiler.extractor.replaceAttr(o, attr, f)
			return obj
		return callback

stubgenerators = []
def stubgenerator(f):
	stubgenerators.append(f)

def makeStubs(compiler):
	collector = StubCollector(compiler)
	compiler.extractor.stubs = collector
	for gen in stubgenerators:
		gen(collector)
	return collector