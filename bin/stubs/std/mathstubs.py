from __future__ import absolute_import

from .. stubcollector import stubgenerator

import math

@stubgenerator
def makeMathStubs(collector):
	llfunc        = collector.llfunc
	export        = collector.export
	replaceAttr   = collector.replaceAttr
	fold          = collector.fold
	staticFold    = collector.staticFold
	attachPtr     = collector.attachPtr


	@export
	@attachPtr(math, 'exp')
	@staticFold(lambda v: math.exp(v))
	@llfunc(primitive=True)
	def math_exp(v):
		return allocate(float)

	@export
	@attachPtr(math, 'log')
	@staticFold(lambda v: math.log(v))
	@llfunc(primitive=True)
	def math_log(v):
		return allocate(float)
