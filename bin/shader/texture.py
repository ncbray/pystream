from . import vec

class Sampler(object):
	__slots__ = ()

class Sampler2D(Sampler):
	def size(self, lod):
		# TODO ivec?
		return vec.vec2(1.0, 1.0)

	def texture(self, P):
		# TODO bias
		return vec.vec4(1.0, 1.0, 1.0, 1.0)
