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

class vec3(object):
	__slots__ = 'x', 'y', 'z'
	def __init__(self, x, y, z):
		self.x = x
		self.y = y
		self.z = z

	def __add__(self, other):
		if isinstance(other, vec3):
			return vec3(self.x+other.x, self.y+other.y, self.z+other.z)
		elif isinstance(other, float):
			return vec3(self.x+other, self.y+other, self.z+other)
		else:
			return NotImplemented

	def __sub__(self, other):
		if isinstance(other, vec3):
			return vec3(self.x-other.x, self.y-other.y, self.z-other.z)
		elif isinstance(other, float):
			return vec3(self.x-other, self.y-other, self.z-other)
		else:
			return NotImplemented

	def __mul__(self, other):
		if isinstance(other, vec3):
			return vec3(self.x*other.x, self.y*other.y, self.z*other.z)
		elif isinstance(other, float):
			return vec3(self.x*other, self.y*other, self.z*other)
		else:
			return NotImplemented

	def __div__(self, other):
		if isinstance(other, vec3):
			return vec3(self.x/other.x, self.y/other.y, self.z/other.z)
		elif isinstance(other, float):
			return vec3(self.x/other, self.y/other, self.z/other)
		else:
			return NotImplemented

	def length(self):
		return self.dot(self)**0.5

	def normalize(self):
		il = 1.0/self.length()
		self.x *= il
		self.y *= il
		self.z *= il

	def dot(self, other):
		x = self.x*other.x
		y = self.y*other.y
		z = self.z*other.z
		return x+y+z

	def cross(self, other):
		x = self.y*other.z-self.z*other.y
		y = self.z*other.x-self.x*other.z
		z = self.x*other.y-self.y*other.x
		return vec3(x, y, z)

	def __repr__(self):
		return "vec3(%f, %f, %f)" % (self.x, self.y, self.z)
