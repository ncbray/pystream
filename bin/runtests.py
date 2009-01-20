#!/c/python25/python
from __future__ import absolute_import

import sys
major, minor = sys.version_info[:2]
if major != 2 or minor < 6:
	print "PyStream requires Python 2.6 to run.  Python %d.%d detected." % (major, minor)
	sys.exit()

import scriptsetup
import config
import testspider

root = scriptsetup.scriptRoot(__file__)
scriptsetup.libraryDirectory(root, "../lib")
if config.usePsyco: scriptsetup.initPsyco()

testList    = getattr(config, 'limitedTest', None)
testExclude = getattr(config, 'testExclude', ())


testspider.runTests(root, testList, testExclude)	
