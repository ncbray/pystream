import sys
import copy
import os
import os.path
import time

#import optimization

from util import CallPath, assureDirectoryExists

from decompiler.programextractor import extractProgram

import imp

# TEST
#import precise	

#import analysis.fiapprox


import analysis.cpa
import analysis.shape

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
		self.filename = filename

		self.rootPath = CallPath(0)
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
		
		execfile(self.filename, makeDSL)

	def pystreamCompile(self):
		print
		print "===================="
		print "===== Frontend ====="
		print "===================="
		print
		self.executeFile()

		if len(self.rawEntryPoints) <= 0:
			print "No entry points, nothing to do."
			return
		
		assert self.outdir, "No output directory declared."

		e, entryPoints = extractProgram(self.moduleName, self.module, self.rawEntryPoints)

		# HACK
		def f():
			dumpFirst = False

			print
			print "============="
			print "=== CPA 1 ==="
			print "============="
			print
			print "Analyize"
			start = time.clock()
			result = analysis.cpa.evaluate(e, entryPoints)
			print "Analysis Time: %.2f" % (time.clock()-start)

			print
			print "Optimize"
			start = time.clock()
			analysis.cpa.optimize(e, entryPoints, result)
			print "Optimize: %.2f" % (time.clock()-start)


			#analysis.shape.evaluate(e, entryPoints, result)

			if False:
				print
				print "============="
				print "=== CPA 2 ==="
				print "============="
				print
				print "Analyize"			
				result = analysis.cpa.evaluate(e, entryPoints)

				print
				print "Optimize"
				analysis.cpa.optimize(e, entryPoints, result)

			print "Dump..."
			start = time.clock()
			analysis.cpa.dump(e, result, entryPoints)
			print "Dump: %.2f" % (time.clock()-start)

			assert False
			
			print
			print "==========================="
			print "===== Analysis Pass 1 ====="
			print "==========================="
			print
			
			analysis.fiapprox.evaluate(self.moduleName, e, entryPoints, dumpFirst, False)

			print
			print "==========================="			
			print "===== Analysis Pass 2 ====="
			print "==========================="
			print
			
			analysis.fiapprox.evaluate(self.moduleName, e, entryPoints, not dumpFirst, True)


		f()
		#cProfile.runctx('f()', globals(), locals())

		#precise.evaluatePrecise(self.moduleName, self.moduleStruct, self.rawEntryPoints, self.rootPath)

		# Compile
		#self.resolver.resolve()

##		# Optimize
##		program = optimization.run(self.entryPoints)
##
##		# Output
		assureDirectoryExists(self.outdir)		
		self.outfile = os.path.join(self.outdir, self.moduleName+'.py')
##		marshal(self, program, self.entryPoints, self.outfile)
