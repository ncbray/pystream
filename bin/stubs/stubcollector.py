from __future__ import absolute_import

from _pystream import cfuncptr
from util import xtypes
from programIR.python import ast

import util

from . import lltranslator

class StubCollector(object):
	def __init__(self, extractor):
		self.extractor = extractor

		self.exports = {}

		self.highLevelGlobals 	= {'method':xtypes.MethodType}
		self.highLevelLUT 	= {}

	##############################
	### AST building utilities ###
	##############################

	def existing(self, obj):
		return ast.Existing(self.extractor.getObject(obj))

	def allocate(self, t, target):
		return ast.Assign(ast.Allocate(t), target)

	def getType(self, inst, result):
		return ast.Assign(ast.Load(inst, 'LowLevel', self.existing('type')), result)

	def loadAttribute(self, expr, type, name, target):
		descriptor  = type.__dict__[name]
		mangledName = util.uniqueSlotName(descriptor)
		return ast.Assign(ast.Load(expr, 'Attribute', self.existing(mangledName)), target)

	def returnNone(self):
		return ast.Return(self.existing(None))

	def typeLookup(self, cls, field, result):
		clsDict = ast.Local('clsDict')
		return [
			ast.Assign(ast.Load(cls, 'LowLevel', self.existing('dictionary')), clsDict),
			ast.Assign(ast.Load(clsDict, 'Dictionary', self.existing(field)), result),
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
				ast.Assign(ast.Call(func, newargs, [], vargs, kargs), result)
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
			callStmt = ast.Assign(call, result)
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

	def llast(self, f):
		code = f()
		assert isinstance(code, ast.Code), type(code)
		self.extractor.desc.functions.append(code)
		return code

	def llfunc(self, func):
		code = self.extractor.decompileFunction(func)
		code = lltranslator.translate(self.extractor, func, code)
		self.extractor.desc.functions.append(code)
		return code

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
			assert isinstance(code, ast.Code), Code
			self.extractor.attachStubToPtr(code, ptr)
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
			assert isinstance(code, ast.Code), code
			self.extractor.attachStubToPtr(code, ptr)

			# Check the binding.
			obj  = self.extractor.getObject(pyobj)
			call = self.extractor.getCall(obj)

			if code is not call:
				print self.extractor.pointerToObject
				print self.extractor.pointerToStub

			assert code is call, (original, pyobj, code, call)

			return code

		return callback

	def fold(self, func):
		def callback(code):
			assert isinstance(code, ast.Code), type(code)
			code.rewriteAnnotation(fold=func)
			return code
		return callback

	def descriptive(self,code):
		assert isinstance(code, ast.Code), type(code)
		code.rewriteAnnotation(descriptive=True)
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
			self.extractor.replaceObject(o, f)
			return f
		return callback

	def replaceAttr(self, o, attr):
		def callback(f):
			assert self.highLevelLUT[f.func_name] == f, "Must declare as high level stub before replacing."
			self.extractor.replaceAttr(o, attr, f)
			return f
		return callback

stubgenerators = []
def stubgenerator(f):
	stubgenerators.append(f)

def makeStubs(extractor):
	collector = StubCollector(extractor)
	extractor.stubs = collector
	for gen in stubgenerators:
		gen(collector)
	return collector