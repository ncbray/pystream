#!/c/python25/python
from __future__ import absolute_import

import scriptsetup
import config
import testspider

root = scriptsetup.scriptRoot(__file__)
scriptsetup.libraryDirectory(root, "../lib")
if config.usePsyco: scriptsetup.initPsyco()

testList    = getattr(config, 'limitedTest', None)
testExclude = getattr(config, 'testExclude', ())


testspider.runTests(root, testList, testExclude)	
