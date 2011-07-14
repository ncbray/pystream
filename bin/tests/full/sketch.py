# Copyright 2011 Nicholas Bray
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#@PydevCodeAnalysisIgnore

from shader.vec import *

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
