import sys
import copy
import os
import os.path

from util import assureDirectoryExists
from decompiler.programextractor import extractProgram
import common.pipeline
from . import compilerconsole

import cProfile


# Thin wrappers made to work with decompiler.programextractor
class InstWrapper(object):
	def __init__(self, typeobj):
		self.typeobj = typeobj

	def getObject(self, extractor):
		return extractor.getInstance(self.typeobj)

class ObjWrapper(object):
	def __init__(self, pyobj):
		self.pyobj = pyobj

	def getObject(self, extractor):
		return extractor.getObject(self.pyobj)

def importDeep(name):
	mod = __import__(name)
	components = name.split('.')
	for comp in components[1:]:
		mod = getattr(mod, comp)
	return mod

class ClassDeclaration(object):
	def __init__(self, cls):
		self.typeobj = cls
		self._init = []
		self._attr = []
		self._method = {}


	def init(self, *args):
		self._init.append(args)

	def attr(self, *args):
		self._attr.extend(args)

	def method(self, name, *args):
		if name not in self._method:
			self._method[name] = []

		self._method[name].append(args)

class ExistingWrapper(object):
	def __init__(self, obj):
		self.obj = obj

	def get(self, dispatcher):
		dispatcher.getExistingArg(self.obj)

class ReturnValueWrapper(object):
	def __init__(self, ep):
		self.ep = ep

	def get(self, dispatcher):
		dispatcher.getReturnArg(self.ep)


class EntryPoint(object):
	__slots__ = 'code', 'selfarg', 'args', 'kwds', 'varg', 'karg', 'group', 'contexts'

	def __init__(self, code, selfarg, args, kwds, varg, karg):
		self.code     = code
		self.selfarg  = selfarg
		self.args     = args
		self.kwds     = kwds
		self.varg     = varg
		self.karg     = karg
		self.group    = None
		self.contexts = []

import util

class InterfaceDeclaration(object):
	__slots__ = 'func', 'cls', 'attr', 'entryPoint', 'translated'

	def __init__(self):

		self.func       = []
		self.cls        = []

		# The memory image
		self.attr       = []

		# Entry points, derived from other declarations.
		self.entryPoint = []

		self.translated = False

	def translate(self, extractor):
		assert not self.translated

		self.entryPoint = []

		self._extractAttr(extractor)
		self._extractFunc(extractor)
		self._extractCls(extractor)

		self.translated = True

	def createEntryPoint(self, code, selfarg, args, kwds, varg, karg, group):
		self.createEntryPointRaw(code, selfarg, args, kwds, varg, karg, group)

	def createEntryPointRaw(self, code, selfarg, args, kwds, varg, karg, group):
		ep = EntryPoint(code, selfarg, args, kwds, varg, karg)
		ep.group = group if group is not None else ep

		self.entryPoint.append(ep)
		return ep

	def _extractFunc(self, extractor):
		newFunc = []

		for expr, args in self.func:
			fobj, code = extractor.getObjectCall(expr)
			argobjs  = [arg.getObject(extractor) for arg in args]

			ep = self.createEntryPoint(code, fobj, argobjs, [], None, None, None)

			newFunc.append((code, fobj, argobjs, ep))

		self.func = newFunc

	def _extractCls(self, extractor):
		for cls in self.cls:
			tobj = extractor.getObject(cls.typeobj)
			inst = extractor.getInstance(cls.typeobj)

			call = extractor.stubs.exports['interpreter_call']
			getter = extractor.stubs.exports['interpreter_getattribute']


			# Type call/init
			group = None
			for args in cls._init:
				ep = self.createEntryPoint(call, tobj, [arg.getObject(extractor) for arg in args], [], None, None, group)
				if group is None: group = ep

			# Attribute getters
			# TODO setters
			for attr in cls._attr:
				name = extractor.getObject(attr)
				ep = self.createEntryPoint(getter, None, [inst, name], [], None, None, None)

			# Method calls
			for name, arglist in cls._method.iteritems():
				# TODO what about inheritance?
				func = cls.typeobj.__dict__[name]
				fobj, code = extractor.getObjectCall(func)

				group = None
				for args in arglist:
					ep = self.createEntryPoint(code, fobj,[inst]+[arg.getObject(extractor) for arg in args], [], None, None, group)
					if group is None: group = ep




	def _extractAttr(self, extractor):
		attrs = []

		for src, attr, dst in self.attr:
			srcobj = src.getObject(extractor)
			# TODO inherited slots?
			attrName = extractor.getObject(util.uniqueSlotName(srcobj.type.pyobj.__dict__[attr]))
			dstobj = dst.getObject(extractor)
			attrs.append((srcobj, ('Attribute', attrName), dstobj))

		self.attr = attrs

	def __nonzero__(self):
		return bool(self.func) or bool(self.cls)


	def entryCode(self):
		assert self.translated
		return frozenset([point.code for point in self.entryPoint])

	def entryContexts(self):
		entryContexts = set()
		for ep in self.entryPoint:
			entryContexts.update(ep.contexts)
		return entryContexts


	def groupedEntryContexts(self):
		assert self.translated
		entryPointMerge = {}
		for entryPoint in self.entryPoint:
			if entryPoint.group not in entryPointMerge:
				entryPointMerge[entryPoint.group] = []
			entryPointMerge[entryPoint.group].extend(entryPoint.contexts)
		return entryPointMerge

class Makefile(object):
	def __init__(self, filename):
		self.filename = os.path.normpath(filename)

		self.moduleName = None
		self.module = None

		self.interface = InterfaceDeclaration()

		self.workingdir = os.path.dirname(os.path.join(sys.path[0], self.filename))
		self.outdir = None

		self.config = {}
		self.config['checkTypes'] = False

	def declModule(self, name):
		self.moduleName = name
		self.module = importDeep(name)

	def declOutput(self, path):
		self.outdir = os.path.normpath(os.path.join(self.workingdir, path))

	def declConst(self, value):
		return ObjWrapper(value)

	def declInstance(self, typename):
		return InstWrapper(typename)

	def declConfig(self, **kargs):
		for k, v in kargs.iteritems():
			self.config[k] = v

	def declAttr(self, src, attr, dst):
		assert isinstance(src, InstWrapper), src
		assert isinstance(dst, InstWrapper), dst
		self.interface.attr.append((src, attr, dst))

	def declFunction(self, funcName, *args):
		assert self.module, "Must declare a module first."
		self.interface.func.append((funcName, args))


	def declClass(self, cls):
		assert isinstance(cls, type), cls
		wrapped = ClassDeclaration(cls)
		self.interface.cls.append(wrapped)
		return wrapped


	def executeFile(self):
		makeDSL = {'module':self.declModule,
			   'const':self.declConst,
			   'inst':self.declInstance,
			   'config':self.declConfig,
			   'attr':self.declAttr,
			   'func':self.declFunction,
			   'cls':self.declClass,
			   'output':self.declOutput}

		f = open(self.filename)
		exec f in makeDSL

	def pystreamCompile(self):
		console = compilerconsole.CompilerConsole()

		console.begin("makefile")
		console.output("Processing %s" % self.filename)
		self.executeFile()
		console.end()

		if not self.interface:
			console.output("No entry points, nothing to do.")
			return

		assert self.outdir, "No output directory declared."

		extractor = extractProgram(self.interface)
		common.pipeline.evaluate(console, self.moduleName, extractor, self.interface)

		# Output
		assureDirectoryExists(self.outdir)
		self.outfile = os.path.join(self.outdir, self.moduleName+'.py')
