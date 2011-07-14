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

from . import ast

void = ast.BuiltinType('void')
bool = ast.BuiltinType('bool')
int = ast.BuiltinType('int')
uint = ast.BuiltinType('uint')
float = ast.BuiltinType('float')
vec2 = ast.BuiltinType('vec2')
vec3 = ast.BuiltinType('vec3')
vec4 = ast.BuiltinType('vec4')
bvec2 = ast.BuiltinType('bvec2')
bvec3 = ast.BuiltinType('bvec3')
bvec4 = ast.BuiltinType('bvec4')
ivec2 = ast.BuiltinType('ivec2')
ivec3 = ast.BuiltinType('ivec3')
ivec4 = ast.BuiltinType('ivec4')
uvec2 = ast.BuiltinType('uvec2')
uvec3 = ast.BuiltinType('uvec3')
uvec4 = ast.BuiltinType('uvec4')
mat2 = ast.BuiltinType('mat2')
mat3 = ast.BuiltinType('mat3')
mat4 = ast.BuiltinType('mat4')
mat2x2 = ast.BuiltinType('mat2x2')
mat2x3 = ast.BuiltinType('mat2x3')
mat2x4 = ast.BuiltinType('mat2x4')
mat3x2 = ast.BuiltinType('mat3x2')
mat3x3 = ast.BuiltinType('mat3x3')
mat3x4 = ast.BuiltinType('mat3x4')
mat4x2 = ast.BuiltinType('mat4x2')
mat4x3 = ast.BuiltinType('mat4x3')
mat4x4 = ast.BuiltinType('mat4x4')

sampler1D = ast.BuiltinType('sampler1D')
sampler2D = ast.BuiltinType('sampler2D')
sampler3D = ast.BuiltinType('sampler3D')
samplerCube = ast.BuiltinType('samplerCube')
sampler1DShadow = ast.BuiltinType('sampler1DShadow')
sampler2DShadow = ast.BuiltinType('sampler2DShadow')
sampler1DArray = ast.BuiltinType('sampler1DArray')
sampler2DArray = ast.BuiltinType('sampler2DArray')
sampler1DArrayShadow = ast.BuiltinType('sampler1DArrayShadow')
sampler2DArrayShadow = ast.BuiltinType('sampler2DArrayShadow')

isampler1D = ast.BuiltinType('isampler1D')
isampler2D = ast.BuiltinType('isampler2D')
isampler3D = ast.BuiltinType('isampler3D')
isamplerCube = ast.BuiltinType('isamplerCube')
isampler1DArray = ast.BuiltinType('isampler1DArray')
isampler2DArray = ast.BuiltinType('isampler2DArray')

usampler1D = ast.BuiltinType('usampler1D')
usampler2D = ast.BuiltinType('usampler2D')
usampler3D = ast.BuiltinType('usampler3D')
usamplerCube = ast.BuiltinType('usamplerCube')
usampler1DArray = ast.BuiltinType('usampler1DArray')
usampler2DArray = ast.BuiltinType('usampler2DArray')
