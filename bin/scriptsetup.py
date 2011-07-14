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

from __future__ import absolute_import

import sys
import os.path

# Use an external directory for libraries
def libraryDirectory(*path):
	libdir = os.path.normpath(os.path.join(*path))
	sys.path.append(libdir)

def scriptRoot(fn):
	path, fn = os.path.split(fn)
	return path

def profile(f):
	import hotshot, hotshot.stats
	prof = hotshot.Profile("tests.prof")
	result = prof.runcall(f)
	prof.close()
	stats = hotshot.stats.load("tests.prof")
	stats.strip_dirs()
	#stats.sort_stats('cumulative')
	stats.sort_stats('time')
	stats.print_stats(40)
	return result

def initPsyco(psycoProfile=False):
	try:
		import psyco
		if psycoProfile:
			psyco.log()
			psyco.profile()
		else:
			psyco.full()
	except ImportError:
		pass
