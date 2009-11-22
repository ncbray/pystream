import random
from shader.vec import *

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

	def __init__(self, material, p, n):
		self.material      = material
		
		self.diffuseColor  = vec3(1.0, 1.0, 1.0)
		self.specularColor = vec3(1.0, 1.0, 1.0)

		self.diffuseLight  = vec3(0.0, 0.0, 0.0)
		self.specularLight = vec3(0.0, 0.0, 0.0)

		self.p = p
		self.n = n
		self.e = -p.normalize()

	def accumulateLight(self, l, amt):
		self.diffuseLight  += self.material.diffuseTransfer(self.n, l, self.e)*amt
		self.specularLight += self.material.specularTransfer(self.n, l, self.e)*amt

	def litColor(self):
		return self.diffuseColor*self.diffuseLight+self.specularColor*self.specularLight
	

class Material(object):
	__slots__ = 'diffuseColor', 'specularColor'
	def __init__(self):
		self.diffuseColor  = vec3(0.125, 0.125, 1.0)
		self.specularColor = vec3(0.5, 0.5, 0.5)

	def diffuseTransfer(self, n, l, e):
		return nldot(n, l)

	def specularTransfer(self, n, l, e):
		return 0.0

	def surface(self, p, n):
		surface = SurfaceFragment(self, p, n)
		surface.diffuseColor  = self.diffuseColor
		surface.specularColor = self.specularColor
		return surface

class LambertMaterial(Material):
	pass

class DummyMaterial(Material):
	pass

class PhongMaterial(Material):
	__slots__ = 'shinny'

	def __init__(self, shinny):
		Material.__init__(self)
		self.shinny = shinny

	def specularTransfer(self, n, l, e):
		# Blinn-Phong transfer
		h = (l+e).normalize()
		ndh = nldot(n, h)		
		# Scale by (shinny+8)/8 to approximate energy conservation
		scale = (self.shinny+8.0)*0.125
		return (ndh**self.shinny)*scale


class Light(object):
	__slots__ = ()

class AmbientLight(Light):
	__slots__ = 'direction', 'color0', 'color1'

	def __init__(self, direction, color0, color1):
		self.direction = direction
		self.color0 = color0
		self.color1 = color1

			
	def accumulate(self, surface, w2c):
		# Transform the direction into world space
		dir = self.direction
		cdir = (w2c*vec4(dir.x, dir.y, dir.z, 0.0)).xyz

		# Blend the hemispheric colors
		amt = cdir.dot(surface.n)*0.5+0.5
		color = self.color1.mix(self.color0, amt)
		
		# Add directly to diffuse, no transfer functions
		surface.diffuseLight += color
	
class PointLight(Light):
	__slots__ = 'position', 'color', 'attenuation'
	
	def __init__(self, position, color, attenuation):
		self.position    = position
		self.color       = color
		self.attenuation = attenuation
			
	def accumulate(self, surface, w2c):
		p = self.position
		pos = (w2c*vec4(p.x, p.y, p.z, 1.0)).xyz

		dir    = pos-surface.p
		dist2  = dir.dot(dir)
		dist   = dist2**0.5
		dists  = vec3(1.0, dist, dist2)
		
		lightAtten = 1.0/dists.dot(self.attenuation)
		
		surface.accumulateLight(dir/dist, self.color*lightAtten)
		

class Shader(object):
	__slots__ = 'objectToWorld', 'worldToCamera', 'projection', 'light', 'ambient', 'material', 'sampler'
	def __init__(self):
		self.objectToWorld = mat4(1.0, 0.0, 0.0, 0.0,
					  0.0, 1.0, 0.0, 0.0,
					  0.0, 0.0, 1.0, 0.0,
					  0.0, 0.0, 0.0, 1.0)


		self.worldToCamera = mat4(1.0, 0.0, 0.0, 0.0,
					  0.0, 1.0, 0.0, 0.0,
					  0.0, 0.0, 1.0, 0.0,
					  0.0, 0.0, 0.0, 1.0)

		self.projection = mat4(1.0, 0.0, 0.0, 0.0,
					  0.0, 1.0, 0.0, 0.0,
					  0.0, 0.0, 1.0, 0.0,
					  0.0, 0.0, 0.0, 1.0)

		self.light = PointLight(vec3(0.0, 10.0, 0.0), vec3(1.0, 1.0, 1.0), vec3(0.01, 0.0, 0.00001))

		self.ambient = AmbientLight(vec3(0.0, 1.0, 0.0), vec3(0.25, 0.75, 0.25), vec3(0.75, 0.25, 0.25))

		self.material = Material()
		
		self.sampler  = None

	def shadeVertex(self, context, pos, normal, texCoord):
		trans     = self.worldToCamera*self.objectToWorld
		newpos    = trans*pos
		newnormal = trans*vec4(normal.x, normal.y, normal.z, 0.0)

		context.position = self.projection*newpos

		return newpos.xyz, newnormal.xyz, texCoord

	def shadeFragment(self, context, pos, normal, texCoord):
		surface = self.material.surface(pos, normal.normalize())

		# Texture
		surface.diffuseColor *= self.sampler.texture(texCoord).xyz
		
		# Accumulate lighting
		self.ambient.accumulate(surface, self.worldToCamera)
		self.light.accumulate(surface, self.worldToCamera)
					
		mainColor = surface.litColor()

		mainColor = rgb2srgb(tonemap(mainColor))
		
		mainColor = vec4(mainColor.x, mainColor.y, mainColor.z, 1.0)
		context.colors = (mainColor,)

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
