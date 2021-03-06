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

import sys
import os.path

from decompiler.programextractor import extractProgram
import application.pipeline
from util.application.console import Console

from . import context
from . program import Program

from . import interface

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
		return interface.ExistingWrapper(value)

	def declInstance(self, typename):
		return interface.InstanceWrapper(typename)

	def declConfig(self, **kargs):
		for k, v in kargs.iteritems():
			self.config[k] = v

	def declFunction(self, func, *args):
		self.interface.func.append((func, args))

	def declClass(self, cls):
		assert isinstance(cls, type), cls
		wrapped = interface.ClassDeclaration(cls)
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
			   'func':self.declFunction,
			   'cls':self.declClass,

			   # GLSL declarations
			   'glsl':self.interface.glsl,
			   'attrslot':interface.AttrDeclaration,
			   'arrayslot':interface.ArrayDeclaration,
			   }

		f = open(self.filename)
		exec f in makeDSL

	def pystreamCompile(self):
		compiler = context.CompilerContext(Console())
		prgm = Program()

		self.interface = prgm.interface


		with compiler.console.scope("makefile"):
			compiler.console.output("Processing %s" % self.filename)
			self.executeFile()

			if not self.interface:
				compiler.console.output("No entry points, nothing to do.")
				return

			assert self.outdir, "No output directory declared."

		extractProgram(compiler, prgm)

		application.pipeline.evaluate(compiler, prgm, self.moduleName)
