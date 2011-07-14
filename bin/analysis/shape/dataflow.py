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

from __future__ import absolute_import

class DataflowEnvironment(object):
	__slots__ = '_secondary', 'observers'

	def __init__(self):
		self._secondary   = {}
		self.observers = {}

	def addObserver(self, index, constraint):
		if not index in self.observers:
			self.observers[index] = [constraint]
		else:
			assert constraint not in self.observers[index]
			self.observers[index].append(constraint)

	def merge(self, sys, point, context, index, secondary, canSteal=False):
		assert not secondary.paths.containsAged()

		# Do the merge
		key = (point, context, index)
		if not key in self._secondary:
			self._secondary[key] = secondary if canSteal else secondary.copy()
			changed = True
		else:
			changed = self._secondary[key].merge(secondary)

		# Did we discover any new information?
		if changed and point in self.observers:
			# Make sure the consumers will be re-evaluated.
			for observer in self.observers[point]:
				sys.worklist.addDirty(observer, key)

	def secondary(self, point, context, index):
		key = (point, context, index)
		return self._secondary.get(key)

	def clear(self):
		self._secondary.clear()

# Processes the queue depth first.
class Worklist(object):
	def __init__(self):
		self.worklist = []
		self.dirty = set()
		self.maxLength = 0
		self.steps = 0
		self.usefulSteps = 0

	def addDirty(self, constraint, index):
		self.useful = True
		key = (constraint, index)
		if key not in self.dirty:
			self.dirty.add(key)
			self.worklist.append(key)

	def pop(self):
		key = self.worklist.pop()
		self.dirty.remove(key)
		return key

	def step(self, sys, trace=False):
		# Track statistics
		self.maxLength = max(len(self.worklist), self.maxLength)

		if trace:
			if self.steps%100==0: print ".",
			if self.steps%10000==0:
				print
				sys.dumpStatistics()
		self.steps += 1

		# Process a constraint/index pair
		constraint, index = self.pop()

		self.useful = False

		try:
			constraint.update(sys, index)
		except:
			print "ERROR processing:", constraint, constraint.inputPoint, constraint.outputPoint
			raise

		if self.useful: self.usefulSteps += 1

	def process(self, sys, trace=False, limit=0):
		stop = self.steps+limit
		while self.worklist:
			self.step(sys, trace)

			if limit and self.steps >= stop:
				return False

		return True
