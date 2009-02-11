from __future__ import absolute_import

from . stubcollector import stubgenerator
from . llutil import simpleDescriptor

### Random module ###

@stubgenerator
def makeRandomStubs(collector):
	attachAttrPtr = collector.attachAttrPtr
	descriptive   = collector.descriptive
	llast         = collector.llast
	llfunc        = collector.llfunc
	export        = collector.export
	highLevelStub = collector.highLevelStub
	replaceObject = collector.replaceObject
	replaceAttr   = collector.replaceAttr
	fold          = collector.fold
	attachPtr     = collector.attachPtr

	import _random

	@attachAttrPtr(_random.Random, 'random')
	@descriptive
	@llfunc
	def random_stub(self):
		return allocate(float)

	# HACK where should this be declared?
	import time

	# A function, not a method, so no "self"
	@attachPtr(time.clock)
	@descriptive
	@llfunc
	def clock_stub():
		return allocate(float)
