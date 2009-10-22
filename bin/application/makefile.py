import sys
import copy
import os
import os.path

from util.filesystem import ensureDirectoryExists
from decompiler.programextractor import extractProgram
import application.pipeline
from util import console
from . import context

import cProfile

from interface import *

def importDeep(name):
	mod = __import__(name)
	components = name.split('.')
	for comp in components[1:]:
		mod = getattr(mod, comp)
	return mod

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
		return InstanceWrapper(typename)

	def declConfig(self, **kargs):
		for k, v in kargs.iteritems():
			self.config[k] = v

	def declAttr(self, src, attr, dst):
		assert isinstance(src, InstanceWrapper), src
		assert isinstance(dst, InstanceWrapper), dst
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
		compiler = context.CompilerContext(console.Console())

		with compiler.console.scope("makefile"):
			compiler.console.output("Processing %s" % self.filename)
			self.executeFile()

			if not self.interface:
				compiler.console.output("No entry points, nothing to do.")
				return

			assert self.outdir, "No output directory declared."

		compiler.interface = self.interface
		extractProgram(compiler)

		application.pipeline.evaluate(compiler, self.moduleName)

		# Output
		#ensureDirectoryExists(self.outdir)
		#self.outfile = os.path.join(self.outdir, self.moduleName+'.py')
