import math
import random
from shader.vec import *
from shader import sampler

class Particle(object):
	__slots__ = 'position', 'velocity'

	def __init__(self):
		self.position = vec3(0.0, 0.0, 0.0)
		self.velocity = vec3(0.0, 0.0, 0.0)

	def update(self, a, dt):
		self.position = self.position+self.velocity*dt+a*dt*dt*0.5
		self.velocity = self.velocity+a*dt

	def setPosition(self, x, y, z):
		self.position.x = x
		self.position.y = y
		self.position.z = z

	def __repr__(self):
		return "Particle(%s, %s)" % (repr(self.position), repr(self.velocity))

class AbstractForce(object):
	__slots__ = ()


class SpringForce(AbstractForce):
	__slots__ = 'k', 'b'
	def __init__(self, k, b):
		self.k = k
		self.b = b

	def calculateForce(self, p):
		return p.position*-self.k+p.velocity*-self.b

class GravitationalForce(AbstractForce):
	__slots__ = 'g'
	def __init__(self, g):
		# TODO assert isinstance(g, vec3)
		self.g = g

	def calculateForce(self, p):
		return self.g


def makeRandomPosition():
	x = random.uniform(-1.0, 1.0)
	y = random.uniform(-1.0, 1.0)
	z = random.uniform(-1.0, 1.0)
	return x, y, z


# Create a list of #count particles, all randomly positioned.
def makeSwarm(count):
	swarm = []

	for i in xrange(count):
		p = Particle()
		# TODO inline info call using varargs?
		x, y, z = makeRandomPosition()
		p.setPosition(x, y, z)
		swarm.append(p)

	return swarm

def simulate(swarm, spring, gravity, dt):
	for p in swarm:
		force = spring.calculateForce(p)+gravity.calculateForce(p)
		p.update(force, dt)

# Create 100 random particles, then simulate them
# under the force of a dampened spring and constant gravity.
def simpleUpdate(dt, iterations):
	swarm = makeSwarm(100)

	spring 	= SpringForce(0.5, 0.01)
	gravity = GravitationalForce(vec3(0.0, -1.0, 0.0))

	for i in xrange(iterations):
		simulate(swarm, spring, gravity, dt)

	return swarm

class SurfaceFragment(object):
	__slots__ = 'material', 'p', 'n', 'e', 'diffuseColor', 'specularColor', 'diffuseLight', 'specularLight'

	def __init__(self, material, p, n, e):
		self.material      = material

		self.diffuseColor  = vec3(1.0)
		self.specularColor = vec3(1.0)

		self.diffuseLight  = vec3(0.0)
		self.specularLight = vec3(0.0)

		self.p = p
		self.n = n
		self.e = e

	def accumulateLight(self, l, amt):
		self.diffuseLight  += self.material.diffuseTransfer(self.n, l, self.e)*amt
		self.specularLight += self.material.specularTransfer(self.n, l, self.e)*amt

	def litColor(self):
		return self.diffuseColor*self.diffuseLight+self.specularColor*self.specularLight


class Material(object):
	__slots__ = 'diffuseColor', 'specularColor', 'diffuseMap'
	__fieldtypes__ = {'diffuseColor':vec3, 'specularColor':vec3, 'diffuseMap':sampler.sampler2D}

	def __init__(self):
		self.diffuseColor  = vec3(0.125, 0.125, 1.0)
		self.specularColor = vec3(0.5, 0.5, 0.5)

	def diffuseTransfer(self, n, l, e):
		return nldot(n, l)

	def specularTransfer(self, n, l, e):
		return 0.0

	def surface(self, p, n, e, texCoord):
		surface = SurfaceFragment(self, p, n, e)
		surface.diffuseColor  = self.diffuseColor*self.diffuseMap.texture(texCoord).xyz
		surface.specularColor = self.specularColor
		return surface

class LambertMaterial(Material):
	__slots__ = 'wrap',
	__fieldtypes__ = {'wrap':float}

	def __init__(self, wrap):
		Material.__init__(self)
		self.wrap = wrap

	def diffuseTransfer(self, n, l, e):
		# Wrap lighting - approximates sub-surface scattering
		ndl = n.dot(l)
		wrapped = (ndl+self.wrap)/(1.0+self.wrap)
		return max(wrapped, 0.0)

	def specularTransfer(self, n, l, e):
		return 0.0


def blinnPhong(n, l, e, shiny):
	# Blinn-Phong transfer
	h = (l+e).normalize()
	ndh = nldot(n, h)
	# Scale by (shiny+8)/8 to approximate energy conservation
	scale = (shiny+8.0)*0.125
	return (ndh**shiny)*scale

class PhongMaterial(Material):
	__slots__ = 'shiny',
	__fieldtypes__ = {'shiny':float}

	def __init__(self, shiny):
		Material.__init__(self)
		self.shiny = shiny

	def specularTransfer(self, n, l, e):
		return blinnPhong(n, l, e, self.shiny)


class ToonMaterial(Material):
	__slots__ = 'toonMap',
	__fieldtypes__ = {'toonMap':sampler.sampler2D}


	def __init__(self, toonMap):
		Material.__init__(self)
		self.toonMap = toonMap

	def diffuseTransfer(self, n, l, e):
		amt = n.dot(l)*0.5+0.5
		return self.toonMap.texture(vec2(0.25, amt)).x

	def specularTransfer(self, n, l, e):
		h = (l+e).normalize()
		amt = nldot(n, h)*0.5+0.5
		return self.toonMap.texture(vec2(0.75, amt)).x


class Light(object):
	__slots__ = ()

class AmbientLight(Light):
	__slots__ = 'direction', 'color0', 'color1'
	__fieldtypes__ = {'direction':vec3, 'color0':vec3, 'color1':vec3}

	def __init__(self, direction, color0, color1):
		self.direction = direction
		self.color0 = color0
		self.color1 = color1

	def color(self, edir):
		amt = self.direction.dot(edir)*0.5+0.5
		return  self.color1.mix(self.color0, amt)

	def accumulate(self, surface, w2c):
		# Transform the direction into world space
		dir = self.direction
		cdir = (w2c*vec4(dir, 0.0)).xyz

		# Blend the hemispheric colors
		amt = cdir.dot(surface.n)*0.5+0.5
		color = self.color1.mix(self.color0, amt)

		# Add directly to diffuse, no transfer functions
		surface.diffuseLight += color

class PointLight(Light):
	__slots__ = 'position', 'color', 'attenuation'
	__fieldtypes__ = {'position':vec3, 'color':vec3, 'attenuation':vec3}

	def __init__(self, position, color, attenuation):
		self.position    = position
		self.color       = color
		self.attenuation = attenuation

	def accumulate(self, surface, w2c):
		l, color = self.lightInfo(surface.p, w2c)
		surface.accumulateLight(l, color)

	def lightInfo(self, surfacePosition, w2c):
		lpos = (w2c*vec4(self.position, 1.0)).xyz
		dir    = lpos-surfacePosition
		dist2  = dir.dot(dir)
		dist   = dist2**0.5
		dists  = vec3(1.0, dist, dist2)
		return dir/dist, self.color/dists.dot(self.attenuation)


class Fog(object):
	__slots__ = 'color', 'density'
	__fieldtypes__ = {'color':vec3, 'density':float}

	def __init__(self, color, density):
		self.color = color
		self.density = density

	def apply(self, color, position):
		return self.color.mix(color, math.exp(position.length()*-self.density))


class TangentSpaceBasis(object):
	__slots__ = 'normal', 'tangent', 'bitangent'

	def __init__(self, normal, tangent, bitangent):
		self.normal    = normal
		self.tangent   = tangent
		self.bitangent = bitangent


	def normalize(self):
		self.normal    = self.normal.normalize()
		self.tanget    = self.tangent.normalize()
		self.bitangent = self.bitangent.normalize()


	def fromTangentSpace(self, tsn):
		if False:
			self.normalize()

			n = self.normal
			t = self.tangent
			b = -self.bitangent
		else:
			n = self.normal.normalize()
			t = self.tangent.normalize()
			b = -self.bitangent.normalize()

		# Transform out of tangent space.
		result = vec3(tsn.x*t.x + tsn.y*b.x + tsn.z*n.x,
					  tsn.x*t.y + tsn.y*b.y + tsn.z*n.y,
					  tsn.x*t.z + tsn.y*b.z + tsn.z*n.z)

		return result.normalize()

	def tangentSpaceEye(self, e):
		n = self.normal.normalize()
		t = self.tangent.normalize()
		b = self.bitangent.normalize()

		e = -e

		tse = vec3(-e.dot(t), e.dot(b), e.dot(n))
		return tse

	def parallaxOcclusionAdjust(self, e, texCoord, nm, amount):
		tse = self.tangentSpaceEye(e)

		maxSteps = 64
		nSteps = maxSteps * tse.xy.length()*amount

		dir = tse.xy*amount/(nSteps*tse.z*8.0)
		stepDepth = 1.0/(nSteps)

		# TODO texture LOD?

		depth = 1.0
		diff0 = depth-nm.texture(texCoord).w
		diff1 = diff0

		if diff1 > 0.0:
			while diff1 > 0.0:
				texCoord += dir
				depth -= stepDepth

				diff0 = diff1
				diff1 = depth-nm.textureLod(texCoord, 0.0).w

			# Find the crossover point
			# Beware of a divide by zero, that's why there's an outer if.

			# diff1 is negative, diff0 is positive
			backtrack = diff1/(diff0 - diff1)
			texCoord += backtrack * dir

		return texCoord



	def parallaxAdjust(self, e, texCoord, nm, amount):
		tse = self.tangentSpaceEye(e)

		height = nm.texture(texCoord).a
		offset = amount*(height-1.0);
		texCoord = texCoord + tse.xy*offset

		return texCoord

	def getNormal(self):
		return self.normal.normalize()


class SurfacePerturber(object):
	__slots__ = ['normalmap']
	__fieldtypes__ = {'normalmap':sampler.sampler2D}

	def perturb(self, tsbasis, texCoord, e):
		return texCoord

	def rayDepth(self, texCoord):
		return self.normalmap.textureLod(texCoord, 0.0).w

	def normal(self, tsbasis, texCoord):
		normal = self.normalmap.texture(texCoord).xyz*2.0-1.0
		return tsbasis.fromTangentSpace(normal)


class NoPerturbation(SurfacePerturber):
	__slots__ = ()

	def normal(self, tsbasis, texCoord):
		return tsbasis.getNormal()


class NormalMapPerturbation(SurfacePerturber):
	__slots__ = ()


class ParallaxOcclusionPerturbation(SurfacePerturber):
	__slots__ = ['parallaxAmount']
	__fieldtypes__ = {'parallaxAmount':float}

	def perturb(self, tsbasis, texCoord, e):
		return tsbasis.parallaxOcclusionAdjust(e, texCoord, self.normalmap, self.parallaxAmount)


# Environment
class Environment(object):
	__slots__ = ['worldToCamera', 'projection', 'cameraToEnvironment', 'ambientMap', 'ambient', 'fog', 'exposure']

	__fieldtypes__ = {'worldToCamera':mat4, 'projection':mat4,
					'cameraToEnvironment':mat4, 'ambientMap':sampler.samplerCube,
					'ambient':AmbientLight, 'fog':Fog, 'exposure':float}

	def processSurfaceColor(self, color, p):
		return self.processBufferColor(self.fog.apply(color, p))

	def processOutputColor(self, color):
		return rgb2srgb(tonemap(color*self.exposure))

	def processBufferColor(self, color):
		return color

	def clearColor(self):
		return self.processOutputColor(self.fog.color)

	def ambientColor(self, n):
		edir = transformNormal(self.cameraToEnvironment, n)
		return self.ambientMap.texture(edir).xyz
		#return self.ambient.color(edir)

def packGBuffer(color, albedo, specular, position, normal):
	return (vec4(color, 1.0), vec4(albedo, specular), vec4(position, 1.0), vec4(normal, 1.0))

def packDistantGBuffer(color):
	surfaceColor = vec4(0.0, 0.0, 0.0, 0.0)
	normal   = vec3(0.0, 0.0, 1.0)
	position = vec3(0.0, 0.0, 10000000.0)

	return (vec4(color, 1.0), surfaceColor, vec4(position, 1.0), vec4(normal, 1.0))

class GBuffer(object):
	__slots__ = ['color', 'surface', 'position', 'normal']
	__fieldtypes__ = {'color':sampler.sampler2D, 'surface':sampler.sampler2D,
					'position':sampler.sampler2D, 'normal':sampler.sampler2D}

	def allocate(self, fbo, width, height):
		self.color    = fbo.createTextureTarget(width, height)
		self.surface  = fbo.createTextureTarget(width, height)
		self.position = fbo.createTextureTarget(width, height)
		self.normal   = fbo.createTextureTarget(width, height)

	def bindForWriting(self, fbo):
		fbo.bind()
		fbo.bindColorAttachment(0, self.color.textureData)
		fbo.bindColorAttachment(1, self.surface.textureData)
		fbo.bindColorAttachment(2, self.position.textureData)
		fbo.bindColorAttachment(3, self.normal.textureData)
		fbo.drawBuffers([0, 1, 2, 3])

	def unpack(self, coord):
		surface  = self.surface.texture(coord)
		position = self.position.texture(coord)
		normal   = self.normal.texture(coord)
		return surface.xyz, surface.w, position.xyz, normal.xyz


class Shader(object):
	__slots__ = ['objectToWorld', 'light',
				'material', 'perturb',
				'env']

	__fieldtypes__ = {'objectToWorld':mat4, 'light':PointLight,
				'material':(LambertMaterial, PhongMaterial, ToonMaterial),
				'perturb':(NoPerturbation, NormalMapPerturbation, ParallaxOcclusionPerturbation),
				'env':Environment,}

	def createTSBasis(self, trans, normal, tangent, bitangent):
		newnormal  = transformNormal(trans, normal)
		newtangent = transformNormal(trans, tangent.xyz)
		#newtangent = vec4(newtangent, tangent.w)
		newbitangent  = transformNormal(trans, bitangent)

		return TangentSpaceBasis(newnormal, newtangent, newbitangent)

	def shadeVertex(self, context, pos, normal, tangent, bitangent, texCoord):
		trans      = self.env.worldToCamera*self.objectToWorld
		newpos     = trans*pos

		tsbasis = self.createTSBasis(trans, normal, tangent, bitangent)

		context.position = self.env.projection*newpos

		return newpos.xyz, tsbasis, texCoord

	def shadeFragment(self, context, pos, tsbasis, texCoord):
		e = -pos.normalize()

		# TODO control flow mutual exclusivity
		texCoord = self.perturb.perturb(tsbasis, texCoord, e)
		normal   = self.perturb.normal(tsbasis, texCoord)

		surface = self.material.surface(pos, normal, e, texCoord)

		# Accumulate lighting
		surface.diffuseLight += self.env.ambientColor(surface.n)
		self.light.accumulate(surface, self.env.worldToCamera)

		mainColor = self.env.processSurfaceColor(surface.litColor(), surface.p)

		context.colors = packGBuffer(mainColor, surface.diffuseColor, surface.specularColor.r, pos, normal)


class SkyBox(object):
	__slots__ = ['objectToWorld', 'sampler', 'env']

	__fieldtypes__ = {'objectToWorld':mat4, 'sampler':sampler.samplerCube, 'env':Environment,}

	def __init__(self):
		self.objectToWorld = mat4(1.0, 0.0, 0.0, 0.0,
					  0.0, 1.0, 0.0, 0.0,
					  0.0, 0.0, 1.0, 0.0,
					  0.0, 0.0, 0.0, 1.0)

		self.env     = None

	def objectToCamera(self):
		return self.env.worldToCamera*self.objectToWorld

	def shadeVertex(self, context, pos):
		trans      = self.objectToCamera()
		newpos     = trans*pos
		context.position = self.env.projection*newpos
		return pos.xyz,

	def shadeFragment(self, context, texCoord):
		albedo = self.sampler.texture(texCoord).xyz
		mainColor = self.env.processBufferColor(albedo)
		context.colors = packDistantGBuffer(mainColor)


class FullScreenEffect(object):
	__slots__ = []
	__fieldtypes__ = {}

	def shadeVertex(self, context, pos, texCoord):
		context.position = pos
		return texCoord,

	def shadeFragment(self, context, texCoord):
		context.colors = (self.process(texCoord),)

class LightPass(FullScreenEffect):
	__slots__ = ['gbuffer', 'light', 'env']

	__fieldtypes__ = {'gbuffer':GBuffer, 'light':PointLight, 'env':Environment,}

	def process(self, texCoord):
		diffuse, specular, position, normal = self.gbuffer.unpack(texCoord)

		e = -position.normalize()

		l, color = self.light.lightInfo(position, self.env.worldToCamera)
		lit = (diffuse*nldot(normal, l)+blinnPhong(normal, l, e, 100.0)*specular)*color
		return vec4(lit, 1.0)


class RadialBlur(FullScreenEffect):
	__slots__ = ['colorBuffer', 'blurBuffer', 'samples', 'scaleFactor', 'falloff', 'bias', 'blurAmount', 'radialAmount', 'env']

	__fieldtypes__ = {'colorBuffer':sampler.sampler2D, 'blurBuffer':sampler.sampler2D,
					'samples':int, 'scaleFactor':float, 'falloff':float, 'bias':float,
					'blurAmount':float, 'radialAmount':float,
					'env':Environment,}

	def __init__(self):
		self.colorBuffer = None

	def computeRadial(self, texCoord):
		color  = vec4(0.0)
		scale  = 1.0
		amount = 1.0
		weight = 0.0

		i = 0

		while i < self.samples:
			# Shift to the center
			uv = (texCoord-0.5)*scale+0.5
			scale *= self.scaleFactor

			# Weighted sample
			color += self.blurBuffer.texture(uv, self.bias)*amount
			weight += amount
			amount *= self.falloff

			i += 1

		return color/weight

	def process(self, texCoord):
		original = self.colorBuffer.texture(texCoord)
		blured   = self.blurBuffer.texture(texCoord)
		color    = original.mix(blured, self.blurAmount)

		color += self.computeRadial(texCoord)*self.radialAmount

		return vec4(self.env.processOutputColor(color.xyz), 1.0)


class DirectionalBlur(FullScreenEffect):
	__slots__ = ['colorBuffer', 'offset']

	__fieldtypes__ = {'colorBuffer':sampler.sampler2D, 'offset':vec2}

	def __init__(self):
		self.colorBuffer = None


	def process(self, texCoord):
		color = self.colorBuffer.texture(texCoord)
		color += self.colorBuffer.texture(texCoord+self.offset)*0.825
		color += self.colorBuffer.texture(texCoord-self.offset)*0.825
		color += self.colorBuffer.texture(texCoord+self.offset*2.0)*0.384
		color += self.colorBuffer.texture(texCoord-self.offset*2.0)*0.384

		weight = (1.0+0.825*2.0+0.384*2.0)

		return color/weight


def transformNormal(m, n):
	return (m*vec4(n, 0.0)).xyz

# TODO clamp?
def fresnel(n, e):
	return min(max(1.0-n.dot(-e), 0.0), 1.0)**5.0

def nldot(a, b):
	return max(a.dot(b), 0.0)

def rgb2srgb(color):
	scale = color*12.92
	warp = (color**(1.0/2.4))*1.055-0.055
	return scale.min(warp)

def rgbLuminance(color):
	return color.dot(vec3(0.2125, 0.7154, 0.0721))

def srgbLuma(color):
	return color.dot(vec3(0.299, 0.587, 0.114))

def tonemap(color):
	L = rgbLuminance(color)
	maxL  = 4.0
	scale = (1.0+L/(maxL*maxL))/(1.0+L)
	return color*scale
