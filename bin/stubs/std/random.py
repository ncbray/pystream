from __future__ import absolute_import

from .. stubcollector import stubgenerator

import _random
import time

@stubgenerator
def makeRandomStubs(collector):
	descriptive   = collector.descriptive
	llfunc        = collector.llfunc
	export        = collector.export
	highLevelStub = collector.highLevelStub
	replaceObject = collector.replaceObject
	replaceAttr   = collector.replaceAttr
	fold          = collector.fold
	attachPtr     = collector.attachPtr


	@attachPtr(_random.Random, 'random')
	@descriptive
	@llfunc
	def random_stub(self):
		return allocate(float)

	# HACK where should this be declared?
	# A function, not a method, so no "self"
	@attachPtr(time.clock)
	@descriptive
	@llfunc
	def clock_stub():
		return allocate(float)
