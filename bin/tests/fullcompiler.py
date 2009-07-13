import time
import imp
from application.makefile import Makefile

compileCache = {}
loadCache    = {}

def compileExample(filename):
	# Done in two phases, as the compilation can
	# succeed but generate bogus code, which prevents import.
	# Compiling multiple times may be problematic, as globals are used.
	if not filename in compileCache:
		make = Makefile(filename)

		start = time.clock()
		make.pystreamCompile()
		end = time.clock()


		if True:
			print
			print "Compile time: %.3f sec" % (end-start)

		compileCache[filename] = make

	return None, None # HACK prevents further compilation

	if not filename in loadCache:
		make = compileCache[filename]

		module = make.module

		# HACK mangle the module name
		generated = imp.load_source(make.moduleName+'gen', make.outfile)

		loadCache[filename] = (module, generated)

	return loadCache[filename]
