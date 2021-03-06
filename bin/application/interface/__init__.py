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

import util
from argwrapper import *
from glsl import *

class ClassDeclaration(object):
	def __init__(self, cls):
		self.typeobj = cls
		self._init   = []
		self._attr   = []
		self._method = {}

	def init(self, *args):
		self._init.append(args)

	def attr(self, *args):
		self._attr.extend(args)

	def method(self, name, *args):
		if name not in self._method:
			self._method[name] = []

		self._method[name].append(args)


class EntryPoint(object):
	__slots__ = 'code', 'selfarg', 'args', 'kwds', 'varg', 'karg', 'group', 'contexts'

	def __init__(self, code, selfarg, args, kwds, varg, karg):
		assert isinstance(selfarg, ArgumentWrapper), selfarg

		for arg in args:
			assert isinstance(arg, ArgumentWrapper), arg

		assert not kwds

		assert isinstance(varg, ArgumentWrapper), varg
		assert isinstance(karg, ArgumentWrapper), karg

		self.code     = code
		self.selfarg  = selfarg
		self.args     = args
		self.kwds     = kwds
		self.varg     = varg
		self.karg     = karg
		self.group    = None
		self.contexts = []

	def name(self):
		return self.code.codeName()

	def __repr__(self):
		return "EntryPoint(%r, %d)" % (self.code, len(self.args))

class InterfaceDeclaration(object):
	__slots__ = 'func', 'cls', 'entryPoint', 'translated', 'glsl'

	def __init__(self):

		self.func       = []
		self.cls        = []

		# Entry points, derived from other declarations.
		self.entryPoint = []

		self.glsl = GLSLDeclaration()

		self.translated = False

	def translate(self, extractor):
		assert not self.translated

		self.entryPoint = []

		self._extractFunc(extractor)
		self._extractCls(extractor)

		self.glsl._extract(extractor, self)

		self.translated = True

	def createEntryPoint(self, code, selfarg, args, kwds=None, varg=None, karg=None, group=None):
		if selfarg is None: selfarg = nullWrapper
		if args is None: args = []
		if kwds is None: kwds = []
		if varg is None: varg = nullWrapper
		if karg is None: karg = nullWrapper

		return self._createEntryPoint(code, selfarg, args, kwds, varg, karg, group)

	def _createEntryPoint(self, code, selfarg, args, kwds, varg, karg, group):
		ep = EntryPoint(code, selfarg, args, kwds, varg, karg)
		ep.group = group if group is not None else ep

		self.entryPoint.append(ep)
		return ep

	def _extractFunc(self, extractor):
		for expr, args in self.func:
			fobj, code = extractor.getObjectCall(expr)

			selfarg  = ExistingWrapper(expr)

			ep = self.createEntryPoint(code, selfarg, tuple(args), [], nullWrapper, nullWrapper, None)

	def getMethCode(self, cls, name, extractor):
		meth = getattr(cls.typeobj, name)
		func = meth.im_func

		fobj, code = extractor.getObjectCall(func)
		selfarg  = ExistingWrapper(func)
		return selfarg, code


	def _extractCls(self, extractor):
		for cls in self.cls:
			tobj = ExistingWrapper(cls.typeobj)
			inst = InstanceWrapper(cls.typeobj)

			call = extractor.stubs.exports['interpreter_call']
			getter = extractor.stubs.exports['interpreter_getattribute']


			# Type call/init
			group = None
			for args in cls._init:
				ep = self.createEntryPoint(call, tobj, args, [], nullWrapper, nullWrapper, group)
				if group is None: group = ep

			# Attribute getters
			# TODO setters
			for attr in cls._attr:
				name = ExistingWrapper(attr)
				ep = self.createEntryPoint(getter, nullWrapper, (inst, name), [], nullWrapper, nullWrapper, None)

			# Method calls
			for name, arglist in cls._method.iteritems():
				selfarg, code = self.getMethCode(cls, name, extractor)

				group = None
				for args in arglist:
					ep = self.createEntryPoint(code, selfarg, (inst,)+args, [], nullWrapper, nullWrapper, group)
					if group is None: group = ep

	def __nonzero__(self):
		return bool(self.func) or bool(self.cls) or bool(self.glsl)


	def entryCode(self):
		return frozenset([point.code for point in self.entryPoint])

	def entryContexts(self):
		entryContexts = set()
		for ep in self.entryPoint:
			entryContexts.update(ep.contexts)
		return entryContexts

	def entryCodeContexts(self):
		entryContexts = set()
		for ep in self.entryPoint:
			for context in ep.contexts:
				entryContexts.add((ep.code, context))
		return entryContexts

	def groupedEntryContexts(self):
		assert self.translated
		entryPointMerge = {}
		for entryPoint in self.entryPoint:
			if entryPoint.group not in entryPointMerge:
				entryPointMerge[entryPoint.group] = []
			entryPointMerge[entryPoint.group].extend(entryPoint.contexts)
		return entryPointMerge
