#@PydevCodeAnalysisIgnore

from __future__ import absolute_import

from .. stubcollector import stubgenerator

import _random
import time

@stubgenerator
def makeRandomStubs(collector):
	llfunc        = collector.llfunc
	export        = collector.export
	replaceAttr   = collector.replaceAttr
	fold          = collector.fold
	attachPtr     = collector.attachPtr


	@attachPtr(_random.Random, 'random')
	@llfunc(descriptive=True)
	def random_stub(self):
		return allocate(float)

	# HACK where should this be declared?
	# A function, not a method, so no "self"
	@attachPtr(time.clock)
	@llfunc(descriptive=True)
	def clock_stub():
		return allocate(float)
