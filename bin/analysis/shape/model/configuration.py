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

noChange = 'nochange'

class Configuration(object):
	__slots__ = 'object', 'region', 'entrySet', 'currentSet', 'externalReferences', 'allocated'
	def __init__(self, object_, region, entrySet, currentSet, externalReferences, allocated):
		assert not (externalReferences and allocated), "Invariant violated."

		self.object     = object_
		self.region     = region
		self.entrySet   = entrySet
		self.currentSet = currentSet
		self.externalReferences = externalReferences
		self.allocated  = allocated

	def slotHit(self, slot):
		return self.currentSet.slotHit(slot)

	def isConfiguration(self):
		return True

	def __repr__(self):
		return "conf(object=%r, entry=%r, current=%r, ex=%r)" % (self.object, self.entrySet, self.currentSet, self.externalReferences)

	def incrementRef(self, sys, slot):
		newrefs = sys.canonical.incrementRef(self.currentSet, slot)
		return [self.rewrite(sys, currentSet=current) for current in newrefs]

	def decrementRef(self, sys, slot):
		newrefs = sys.canonical.decrementRef(self.currentSet, slot)
		return [self.rewrite(sys, currentSet=current) for current in newrefs]

	def forget(self, sys, kill):
		currentSet = self.currentSet.forget(sys, kill)
		return self.rewrite(sys, currentSet=currentSet)

	def rewrite(self, sys,
			object_    = noChange,
			region     = noChange,
			entrySet   = noChange,
			currentSet = noChange,
			externalReferences=noChange,
			allocated  = noChange):

		if object_ is noChange:            object_    = self.object
		if region is noChange:             region     = self.region
		if entrySet is noChange:           entrySet   = self.entrySet
		if currentSet is noChange:         currentSet = self.currentSet
		if externalReferences is noChange: externalReferences = self.externalReferences
		if allocated is noChange:          allocated  = self.allocated

		return sys.canonical.configuration(object_, region, entrySet, currentSet, externalReferences, allocated)
