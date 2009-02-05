from __future__ import absolute_import

from _pystream import cfuncptr
from util import xtypes
from programIR.python import ast

from util import replaceGlobals

class StubCollector(object):
	def __init__(self, extractor):
		self.extractor = extractor

		self.exports = {}

		self.llastLUT = []

		self.ptrAST = []

		self.foldLUT = {}
		self.descriptiveLUT = {}

		self.highLevelGlobals 	= {'method':xtypes.MethodType}
		self.highLevelLUT 	= {}
		self.objectReplacements	= []
		self.attrReplacements	= []

	def export(self, funcast):
		if isinstance(funcast, xtypes.FunctionType):
			name = funcast.func_name
		else:
			name = funcast.name

		assert not name in self.exports
		self.exports[name] = funcast
		return funcast

	def llast(self, f):
		funcast = f()
		self.llastLUT.append(funcast)
		return funcast

	def cfuncptr(self, obj):
		try:
			return cfuncptr(obj)
		except TypeError:
			raise TypeError, "Cannot get pointer from %r" % type(obj)

	### Attachment functions ###

	def attachAttrPtr(self, t, attr):
		assert isinstance(t, type), t
		assert isinstance(attr, str), attr

		meth = getattr(t, attr)
		ptr = self.cfuncptr(meth)

		def callback(funcast):
			assert isinstance(funcast, ast.Function), funcast
			self.ptrAST.append((ptr, funcast))
			return funcast
		return callback


	def attachPtr(self, obj):
		ptr = self.cfuncptr(obj)

		def callback(funcast):
			assert isinstance(funcast, ast.Function), funcast
			self.ptrAST.append((ptr, funcast))
			return funcast
		return callback

	def bindStubs(self, extractor):
		for ptr, funcast in self.ptrAST:
			extractor.attachStubToPtr(funcast, ptr)


	def fold(self, func):
		def callback(funcast):
			assert isinstance(funcast, ast.Function), type(funcast)
			self.foldLUT[funcast.code] = func
			return funcast
		return callback

	def descriptive(self, funcast):
		assert isinstance(funcast, ast.Function), type(funcast)
		self.descriptiveLUT[funcast.code] = True
		return funcast


	##################
	### High Level ###
	##################

	def highLevelStub(self, f):
		# Let the function use the common global dictionary.
		# Recreate the function with different globals.
		f = replaceGlobals(f, self.highLevelGlobals)

		# Register
		self.highLevelLUT[f.func_name] = f

		# Add to the common global dictionary
		self.highLevelGlobals[f.func_name] = f

		return f

	### Attachment functions ###
	def replaceObject(self, o):
		def callback(f):
			assert self.highLevelLUT[f.func_name] == f, "Must declare as high level stub before replacing."
			self.objectReplacements.append((o, f))
			return f
		return callback

	def replaceObjects(self, extractor):
		for o, f in self.objectReplacements:
			extractor.replaceObject(o, f)


	def replaceAttr(self, o, attr):
		def callback(f):
			assert self.highLevelLUT[f.func_name] == f, "Must declare as high level stub before replacing."
			self.attrReplacements.append((o, attr, f))
			return f
		return callback

	def replaceAttrs(self, extractor):
		for o, attr, f in self.attrReplacements:
			extractor.replaceAttr(o, attr, f)

stubgenerators = []
def stubgenerator(f):
	stubgenerators.append(f)

def makeStubs(extractor):
	collector = StubCollector(extractor)
	for gen in stubgenerators:
		gen(collector)
	return collector