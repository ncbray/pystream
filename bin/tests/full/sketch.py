#@PydevCodeAnalysisIgnore

from vec import *

class Shader(object):
	def projected(self, pos):
		raise NotImplemented

	def __call__(self, *args, **kargs):
		raise NotImplemented

class SimpleShader(Shader):
	def __init__(sellf, project):
		self.project = project
	
	def shadeVertex(self, pos, color):
		self.projected(self.project*vec4(pos.x, pos.y, pos.z, 1.0))
		return color

	def shadeFragment(self, color):
		return vec4(color.x, color.y, color.z, 1.0)


# Quick and dirty CPA?
# 	Extract node structure using dataflow analysis.
# 	Node has attributes (node, context, name) -> set(...)
#	Nodes may be conditional on other nodes.
#	Sophisticated call handling?

# Special glsl functions are inserted *during* translation into glsl, not before.
# Before that, vectors and matrices are treated as plain-old datatypes.

# SimpleShader
#	expose get/set project -> mat4
#	mark as shader

# Goals
#	Simple
#	Lit
#	Polymorphic materials
#	Polymorphic lights
#	Parallax occlusion mapping
