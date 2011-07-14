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

class ClassDecl(object):
	def __init__(self, t):
		self.type_ = t
		self.slots = {}
		self.methods = {}
		self.getters = set()

	def slot(self, name, types):
		if not isinstance(types, (tuple, list)):
			types = (types,)

		if name not in self.slots:
			self.slots[name] = list(types)
		else:
			self.slots[name].extend(types)

	def method(self, name, *args):
		if name not in self.methods:
			self.methods[name] = [args]
		else:
			self.methods[name].append(args)

	def getter(self, name):
		self.getters.add(name)


class ShaderDecl(ClassDecl):
	def vertex(self, *types):
		self.vertexIn = types

classes = {}

def class_(t):
	assert t not in classes, t
	cls = ClassDecl(t)
	classes[t] = cls
	return cls

def shader(t):
	assert t not in classes, t
	cls = ShaderDecl(t)
	classes[t] = cls
	return cls
