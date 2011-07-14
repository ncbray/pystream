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

#!/c/python25/python
from __future__ import absolute_import

import sys
import os
major, minor = sys.version_info[:2]
if major != 2 or minor < 6:
	print "PyStream requires Python 2.6 to run.  Python %d.%d detected." % (major, minor)
	sys.exit()

import scriptsetup
import config

root = scriptsetup.scriptRoot(__file__)
scriptsetup.libraryDirectory(root, '..', 'lib')
if config.usePsyco and not config.debugOnFailiure: scriptsetup.initPsyco()


# Get white and black lists for tests
def testConfigToFiles(testFiles):
	return frozenset([os.path.normpath(os.path.join(root, *path)) for path in testFiles])

testOnly    = testConfigToFiles(getattr(config, 'testOnly', ()))
testExclude = testConfigToFiles(getattr(config, 'testExclude', ()))

import testspider
testspider.runTests(root, testOnly, testExclude)
