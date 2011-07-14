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
	@replaceAttr(sampler.samplerCube, 'texture')
	@llfunc(descriptive=True)
	def texture(self, P, bias=None):
		return vec4(allocate(float), allocate(float), allocate(float), allocate(float))

	@export
	@replaceAttr(sampler.sampler2D, 'textureLod')
	@replaceAttr(sampler.samplerCube, 'textureLod')
	@llfunc(descriptive=True)
	def textureLod(self, P, lod):
		return vec4(allocate(float), allocate(float), allocate(float), allocate(float))
