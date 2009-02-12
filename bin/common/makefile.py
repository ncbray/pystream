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


class Makefile(object):
	def __init__(self, filename):
		self.filename = os.path.normpath(filename)

		self.moduleName = None
		self.module = None
		self.moduleStruct = None
		self.entryPoints = []
		self.rawEntryPoints = []

		self.workingdir = os.path.dirname(os.path.join(sys.path[0], self.filename))
		self.outdir = None

		self.config = {}
		self.config['checkTypes'] = False

	def declModule(self, name):
		self.moduleName = name

		oldpath = sys.path
		newpath = copy.copy(sys.path)
		newpath[0] = self.workingdir

		sys.path = newpath
		self.module = __import__(name)
		sys.path = oldpath

	def declOutput(self, path):
		self.outdir = os.path.normpath(os.path.join(self.workingdir, path))

	def declConst(self, value):
		return ObjWrapper(value)

	def declInstance(self, typename):
		return InstWrapper(typename)

	def declConfig(self, **kargs):
		for k, v in kargs.iteritems():
			self.config[k] = v

	# TODO allow direct spesification of function pointer.
	def declEntryPoint(self, funcName, *args):
		assert self.module, "Must declare a module first."
		self.rawEntryPoints.append((funcName, args))

	def executeFile(self):
		makeDSL = {'module':self.declModule,
			   'const':self.declConst,
			   'inst':self.declInstance,
			   'config':self.declConfig,
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

		if len(self.rawEntryPoints) <= 0:
			print "No entry points, nothing to do."
			return

		assert self.outdir, "No output directory declared."

		e, entryPoints = extractProgram(self.moduleName, self.module, self.rawEntryPoints)
		common.pipeline.evaluate(console, self.moduleName, e, entryPoints)

		# Output
		assureDirectoryExists(self.outdir)
		self.outfile = os.path.join(self.outdir, self.moduleName+'.py')
