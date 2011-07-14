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
