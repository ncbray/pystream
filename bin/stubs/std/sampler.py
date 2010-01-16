from shader import sampler, vec

from .. stubcollector import stubgenerator

vec4 = vec.vec4

@stubgenerator
def makeSamplerFunc(collector):
	llfunc        = collector.llfunc
	export        = collector.export
	replaceAttr   = collector.replaceAttr
	attachPtr     = collector.attachPtr

	@export
	@replaceAttr(sampler.sampler2D, 'texture')
	@llfunc(descriptive=True)
	def texture(self, P, bias=None):
		return vec4(allocate(float), allocate(float), allocate(float), allocate(float))
