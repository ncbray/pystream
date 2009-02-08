from __future__ import absolute_import

from . stubcollector import stubgenerator
from . llutil import simpleDescriptor

### Random module ###

@stubgenerator
def makeRandomStubs(collector):
	attachAttrPtr = collector.attachAttrPtr
	descriptive   = collector.descriptive
	llast         = collector.llast
	export        = collector.export
	highLevelStub = collector.highLevelStub
	replaceObject = collector.replaceObject
	replaceAttr   = collector.replaceAttr
	fold          = collector.fold
	attachPtr     = collector.attachPtr

	import _random
	attachAttrPtr(_random.Random, 'random')(llast(simpleDescriptor(collector, 'random', ('self',), float)))

	# HACK where should this be declared?
	import time
	attachPtr(time.clock)(llast(simpleDescriptor(collector, 'clock', ('self',), float)))
