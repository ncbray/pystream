import sys
import copy
import os
import os.path

from util.filesystem import ensureDirectoryExists
from decompiler.programextractor import extractProgram
import common.pipeline
from . import compilerconsole

import cProfile

import util

class ArgWrapper(object):
	pass

# Thin wrappers made to work with decompiler.programextractor
class InstWrapper(ArgWrapper):
	def __init__(self, typeobj):
		self.typeobj = typeobj

	def getObject(self, extractor):
		return extractor.getInstance(self.typeobj)

	def get(self, dataflow):
		return dataflow.getInstanceSlot(self.typeobj)

class ExistingWrapper(ArgWrapper):
	def __init__(self, pyobj):
		self.pyobj = pyobj

	def getObject(self, extractor):
		return extractor.getObject(self.pyobj)

	def get(self, dataflow):
		return dataflow.getExistingSlot(self.pyobj)

class ReturnWrapper(ArgWrapper):
	def __init__(self, ep):
		assert isinstance(ep, EntryPoint), repr(ep)
		self.ep = ep

	def get(self, dataflow):
		return dataflow.getReturnSlot(self.ep)


class NullWrapper(ArgWrapper):
	def get(self, dataflow):
		return None

	def __nonzero__(self):
		return False

nullWrapper = NullWrapper()

def validArg(arg):
	return isinstance(arg, ArgWrapper)


def importDeep(name):
	mod = __import__(name)
	components = name.split('.')
	for comp in components[1:]:
		mod = getattr(mod, comp)
	return mod


# Returns the extacted object, plus the slot name for the attribute.
def extractAttr(extractor, obj, name):
	assert isinstance(obj, ArgWrapper), obj
	objobj = obj.getObject(extractor)
	# TODO inherited slots?
	d = objobj.type.pyobj.__dict__
	assert name in d, "%r does not have attribute %r" % (objobj, name)
	attrName = extractor.getObject(util.uniqueSlotName(d[name]))
	return objobj, ('Attribute', attrName)


class ClassDeclaration(object):
	def __init__(self, cls):
		self.typeobj = cls
		self._init   = []
		self._attr   = []
		self._method = {}
		self._shader = []

	def init(self, *args):
		self._init.append(args)

	def attr(self, *args):
		self._attr.extend(args)

	def method(self, name, *args):
		if name not in self._method:
			self._method[name] = []

		self._method[name].append(args)

	def shader(self, *args):
		self._shader.append(args)


class EntryPoint(object):
	__slots__ = 'code', 'selfarg', 'args', 'kwds', 'varg', 'karg', 'group', 'contexts'

	def __init__(self, code, selfarg, args, kwds, varg, karg):
		assert validArg(selfarg), selfarg

		for arg in args:
			assert validArg(arg), arg

		assert not kwds

		assert validArg(varg), varg
		assert validArg(karg), karg

		self.code     = code
		self.selfarg  = selfarg
		self.args     = args
		self.kwds     = kwds
		self.varg     = varg
		self.karg     = karg
		self.group    = None
		self.contexts = []

### Begin GLSL Stuff ###

class PathDeclaration(object):
	__slots__ = 'parent'

	def attrslot(self, obj, name):
		child = AttrDeclaration(obj, name)
		child.parent = self
		return child

	def arrayslot(self, index):
		child = ArrayDeclaration(index)
		child.parent = self
		return child

	def extract(self, extractor):
		part = (self._extractPart(extractor),)

		if(self.parent):
			return self.parent.extract(extractor) + part
		else:
			return part


class AttrDeclaration(PathDeclaration):
	__slots__ = 'obj', 'name'

	def __init__(self, obj, name):
		assert isinstance(obj, ArgWrapper), obj
		assert isinstance(name, str), name

		self.parent = None
		self.obj = obj
		self.name = name

	def _extractPart(self, extractor):
		objobj, slot = extractAttr(extractor, self.obj, self.name)
		return slot

class ArrayDeclaration(PathDeclaration):
	__slots__ = 'index'

	def __init__(self, index):
		assert isinstance(index, int), index

		self.parent = None
		self.index = index

	def _extractPart(self, extractor):
		return ('Array', extractor.getObject(self.index))

# A extension to the makefile for spesifying glsl-spesific things.
class GLSLDeclaration(object):
	def __init__(self):
		self.attr = []

	def input(self, path, name):
		self._attr(path, name, True, False)

	def output(self, path, name):
		self._attr(path, name, False, True)

	def inout(self, path, name):
		self._attr(path, name, True, True)

	# Declares that the specified path through the heap should be replaced
	# with a special variable named "name".
	def _attr(self, path, name, input, output):
		assert isinstance(path, PathDeclaration), path
		assert isinstance(name, str), name
		self.attr.append((path, name, input, output))

	def _extract(self, extractor):
		attr = []

		for path, name, input, output in self.attr:
			newpath = path.extract(extractor)
			attr.append((newpath, name, input, output))

		self.attr = attr

### End GLSL Stuff ###

class InterfaceDeclaration(object):
	__slots__ = 'func', 'cls', 'attr', 'entryPoint', 'translated', 'glsl'

	def __init__(self):

		self.func       = []
		self.cls        = []

		# The memory image
		self.attr       = []

		# Entry points, derived from other declarations.
		self.entryPoint = []

		self.glsl = GLSLDeclaration()

		self.translated = False

	def translate(self, extractor):
		assert not self.translated

		self.entryPoint = []

		self._extractAttr(extractor)
		self._extractFunc(extractor)
		self._extractCls(extractor)

		self.glsl._extract(extractor)

		self.translated = True

	def createEntryPoint(self, code, selfarg, args, kwds, varg, karg, group):
		return self.createEntryPointRaw(code, selfarg, args, kwds, varg, karg, group)

	def createEntryPointRaw(self, code, selfarg, args, kwds, varg, karg, group):
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
		# TODO what about inheritance?
		func = cls.typeobj.__dict__[name]
		fobj, code = extractor.getObjectCall(func)
		selfarg  = ExistingWrapper(func)
		return selfarg, code


	def _extractCls(self, extractor):
		for cls in self.cls:
			tobj = ExistingWrapper(cls.typeobj)
			inst = InstWrapper(cls.typeobj)

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

			vsGroup = None
			fsGroup = None

			for args in cls._shader:
				selfarg, code = self.getMethCode(cls, 'shadeVertex', extractor)
				vep = self.createEntryPoint(code, selfarg, (inst,)+args, [], nullWrapper, nullWrapper, vsGroup)

				selfarg, code = self.getMethCode(cls, 'shadeFragment', extractor)
				fep = self.createEntryPoint(code, selfarg, (inst,), [], ReturnWrapper(vep), nullWrapper, fsGroup)

	def _extractAttr(self, extractor):
		attrs = []

		for src, attr, dst in self.attr:
			srcobj, attrName = extractAttr(extractor, src, attr)
			dstobj = dst.getObject(extractor)
			attrs.append((srcobj, attrName, dstobj))

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
		return ExistingWrapper(value)

	def declInstance(self, typename):
		return InstWrapper(typename)

	def declConfig(self, **kargs):
		for k, v in kargs.iteritems():
			self.config[k] = v

	def declAttr(self, src, attr, dst):
		assert isinstance(src, InstWrapper), src
		assert isinstance(dst, InstWrapper), dst
		self.interface.attr.append((src, attr, dst))

	def declFunction(self, func, *args):
		self.interface.func.append((func, args))

	def declClass(self, cls):
		assert isinstance(cls, type), cls
		wrapped = ClassDeclaration(cls)
		self.interface.cls.append(wrapped)
		return wrapped


	def executeFile(self):
		makeDSL = {
			   # Meta declarations
			   'module':self.declModule,
			   'output':self.declOutput,
			   'config':self.declConfig,

			   # Argument declarations
			   'const':self.declConst,
			   'inst':self.declInstance,

			   # Interface declarations
			   'attr':self.declAttr,
			   'func':self.declFunction,
			   'cls':self.declClass,

			   # GLSL declarations
			   'glsl':self.interface.glsl,
			   'attrslot':AttrDeclaration,
			   'arrayslot':ArrayDeclaration,
			   }

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
		ensureDirectoryExists(self.outdir)
		self.outfile = os.path.join(self.outdir, self.moduleName+'.py')
