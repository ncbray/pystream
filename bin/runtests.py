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
if config.usePsyco: scriptsetup.initPsyco()


# Get white and black lists for tests
def testConfigToFiles(testFiles):
	return frozenset([os.path.normpath(os.path.join(root, *path)) for path in testFiles])

testOnly    = testConfigToFiles(getattr(config, 'testOnly', ()))
testExclude = testConfigToFiles(getattr(config, 'testExclude', ()))

import testspider
testspider.runTests(root, testOnly, testExclude)


