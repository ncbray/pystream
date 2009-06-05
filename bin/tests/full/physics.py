import random
from vec import *

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

class Material(object):
	__slots__ = 'color'
	def __init__(self):
		self.color = vec3(0.125, 0.125, 1.0)

class VSOut(object):
	__slots__ = 'position', 'point_size'

class FSIn(object):
	__slots__ = 'coord', 'depth', 'front_facing',

class FSOut(object):
	__slots__ = 'colors', 'depth'

class Shader(object):
	__slots__ = 'objectToWorld', 'worldToCamera', 'projection', 'lightPos', 'ambient', 'material'
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

		self.lightPos = vec4(0.0, 10.0, 0.0, 1.0)

		self.ambient = vec3(0.25, 0.25, 0.25)

		self.material = Material()

	def shadeVertex(self, pos, normal):
		trans     = (self.worldToCamera*self.objectToWorld)
		newpos    = (trans*pos)
		projected = self.projection*newpos
		newnormal = (trans*vec4(normal.x, normal.y, normal.z, 0.0)).xyz

		vsout = VSOut()
		vsout.position = projected

		return vsout, (newpos.xyz, newnormal)

	def shadeFragment(self, pos, normal):
		n = normal.normalize()

		if True:
			mainColor = n*0.5+vec3(0.5, 0.5, 0.5)

		else:
			# Light into camera space
			trans = self.worldToCamera
			lightPos = trans*self.lightPos

			lightDir  = lightPos.xyz-pos.xyz
			lightDist = lightDir.length()
			lightDir  = lightDir/lightDist

			lightAtten = 1.0/(0.01+lightDist*lightDist)
			transfer = nldot(lightDir, n)
			modulated = transfer*lightAtten

			mainColor = self.material.color*(self.ambient+modulated)

		fsout = FSOut()
		fsout.colors = (mainColor,)
		return fsout

def nldot(a, b):
	return max(a.dot(b), 0.0)



def harness(pos, normal):
	shader = Shader()
	pos, normal, color = shader.shadeVertex(pos, normal)
	finalColor = shader.shadeFragment(pos, normal, color)
	return finalColor