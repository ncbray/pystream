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

from util.typedispatch import *
from language.glsl import ast as glsl

class MakeAssign(TypeDispatcher):
	@dispatch(type(None))
	def visitNone(self, dst, src):
		return glsl.Discard(src)

	@dispatch(glsl.Local)
	def visitLocal(self, dst, src):
		return glsl.Assign(src, dst)

	@dispatch(glsl.GetSubscript)
	def visitSetSubscript(self, dst, src):
		return glsl.SetSubscript(src, dst.expr, dst.subscript)

	@dispatch(glsl.GetAttr)
	def visitGetAttr(self, dst, src):
		return glsl.SetAttr(src, dst.expr, dst.name)

	@dispatch(glsl.Load)
	def visitLoad(self, dst, src):
		return glsl.Store(src, dst.expr, dst.name)

_makeAssign = MakeAssign()

def assign(src, dst):
	return _makeAssign(dst, src)
