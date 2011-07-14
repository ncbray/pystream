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

from . import pathinformation

class SecondaryInformation(object):
	__slots__ = 'paths', 'externalReferences'
	def __init__(self, paths, externalReferences):
		self.paths = paths
		self.externalReferences = externalReferences

	def merge(self, other):
		paths, pathsChanged = self.paths.inplaceMerge(other.paths)
		if pathsChanged:
			self.paths = paths

		if self.externalReferences == False and other.externalReferences == True:
			self.externalReferences = True
			externalChanged = True
		else:
			externalChanged = False

		return pathsChanged or externalChanged

	def __repr__(self):
		return "secondary(..., external=%r)" % (self.externalReferences,)

	def copy(self):
		return SecondaryInformation(self.paths.copy(), self.externalReferences)

	def forget(self, sys, kill):
		return sys.canonical.secondary(self.paths.forget(kill), self.externalReferences)
