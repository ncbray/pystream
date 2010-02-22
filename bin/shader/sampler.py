from . import vec

class Sampler(object):
	__slots__ = ()

class sampler2D(Sampler):
	__slots__ = 'textureData',

	def size(self, lod):
		# TODO ivec?
		return vec.vec2(1.0, 1.0)

	def texture(self, P, bias=None):
		return vec.vec4(1.0, 1.0, 1.0, 1.0)

	def textureLod(self, P, lod):
		return vec.vec4(1.0, 1.0, 1.0, 1.0)

class samplerCube(Sampler):
	__slots__ = 'textureData',

	def size(self, lod):
		# TODO ivec?
		return vec.vec2(1.0, 1.0, 1.0)

	def texture(self, P, bias=None):
		return vec.vec4(1.0, 1.0, 1.0, 1.0)
	
	def textureLod(self, P, lod):
		return vec.vec4(1.0, 1.0, 1.0, 1.0)
