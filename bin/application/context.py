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

from util.python import uniqueSlotName
import collections

class Slots(object):
	def __init__(self):
		self.cache   = {}
		self.reverse = {}

	def uniqueSlotName(self, descriptor):
		if descriptor in self.cache:
			return self.cache[descriptor]

		uniqueName = uniqueSlotName(descriptor)

		self.cache[descriptor]   = uniqueName
		self.reverse[uniqueName] = descriptor

		return uniqueName

class CompilerContext(object):
	__slots__ = 'console', 'extractor', 'slots', 'stats'

	def __init__(self, console):
		self.console    = console
		self.extractor  = None
		self.slots      = Slots()
		self.stats      = collections.defaultdict(dict)
