# Copyright 2011 Nicholas Bray
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import

from _pystream import cfuncptr
from util.monkeypatch import xtypes

from util.python import replaceGlobals

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
			code.rewriteAnnotation(runtime=True)

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
		code.rewriteAnnotation(descriptive=True, primitive=True, runtime=False, interpreter=False)
		return code

	def replaceAttr(self, o, attr):
		def callback(obj):
			if not isinstance(obj, xtypes.FunctionType):
				assert obj.isCode(), type(obj)
				f = self.codeToFunction[obj]
			else:
				f = obj
				#assert self.highLevelLUT[f.func_name] == f, "Must declare as high level stub before replacing."
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
