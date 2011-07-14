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

class ArgumentWrapper(object):
	pass

# Thin wrappers made to work with decompiler.programextractor
class InstanceWrapper(ArgumentWrapper):
	def __init__(self, typeobj):
		self.typeobj = typeobj

	def getObject(self, extractor):
		return extractor.getInstance(self.typeobj)

	def get(self, dataflow):
		return dataflow.getInstanceSlot(self.typeobj)

class ExistingWrapper(ArgumentWrapper):
	def __init__(self, pyobj):
		self.pyobj = pyobj

	def getObject(self, extractor):
		return extractor.getObject(self.pyobj)

	def get(self, dataflow):
		return dataflow.getExistingSlot(self.pyobj)

# Used when an argument, such as varg or karg, is not present.
class NullWrapper(ArgumentWrapper):
	def get(self, dataflow):
		return None

	def __nonzero__(self):
		return False

nullWrapper = NullWrapper()
