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
		# This may return "None" if the abstractInstances have not yet been constructed.

		typeobj = extractor.getObject(self.typeobj)
		extractor.ensureLoaded(typeobj)

		return typeobj.abstractInstance()

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


import util

class InterfaceDeclaration(object):
	__slots__ = 'entryPoint',  'attr', 'translated'

	def __init__(self):
		self.entryPoint = []
		self.attr       = []

		self.translated = False

	def translate(self, extractor):
		assert not self.translated

		self._extractAttr(extractor)
		self._extractEntryPoint(extractor)

		self.translated = True

	def _extractEntryPoint(self, extractor):
		entryPoint = []

		for expr, args in self.entryPoint:
			fobj = extractor.getObject(expr)
			extractor.ensureLoaded(fobj)
			func = extractor.getCall(fobj)

			argobjs  = [arg.getObject(extractor) for arg in args]

			entryPoint.append((func, fobj, argobjs))

		self.entryPoint = entryPoint

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
		return bool(self.entryPoint)


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

	# TODO allow direct spesification of function pointer.
	def declEntryPoint(self, funcName, *args):
		assert self.module, "Must declare a module first."
		self.interface.entryPoint.append((funcName, args))

	def executeFile(self):
		makeDSL = {'module':self.declModule,
			   'const':self.declConst,
			   'inst':self.declInstance,
			   'config':self.declConfig,
			   'attr':self.declAttr,
			   'entryPoint':self.declEntryPoint,
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
