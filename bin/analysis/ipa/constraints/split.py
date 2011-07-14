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

from language.python import ast
from . base import Constraint
from .. calling import cpa

class Splitter(Constraint):
	def __init__(self, src):
		assert src.isNode(), src
		self.src = src
		self.dst = []
		self.callbacks = []

	def addSplitCallback(self, callback):
		self.callbacks.append(callback)
		if self.objects: callback()

	def attach(self):
		self.src.addNext(self)

	def localName(self):
		return 'split_temp'

	def makeTarget(self, context):
		lcl = context.local(ast.Local(self.localName()))
		lcl.addPrev(self)
		self.dst.append(lcl)
		return lcl

	def makeConsistent(self, context):
		# Make constraint consistent
		if self.src.values:
			self.changed(context, self.src, self.src.values)

		if self.src.critical.values:
			self.criticalChanged(context, self.src, self.src.critical.values)

	def criticalChanged(self, context, node, diff):
		for dst in self.dst:
			dst.critical.updateValues(context, dst, diff)

	def doNotify(self):
		for callback in self.callbacks:
			callback()

	def isSplit(self):
		return True

class TypeSplitConstraint(Splitter):
	def __init__(self, src):
		Splitter.__init__(self, src)
		self.objects = {}
		self.megamorphic = False

	def localName(self):
		return 'type_split_temp'

	def types(self):
		return self.objects.keys()

	def makeMegamorphic(self):
		assert not self.megamorphic
		self.megamorphic = True
		self.objects.clear()
		self.objects[cpa.anyType] = self.src
		self.doNotify()

	def changed(self, context, node, diff):
		if self.megamorphic: return

		changed = False
		for obj in diff:
			cpaType = obj.cpaType()

			if cpaType not in self.objects:
				if len(self.objects) >= 4:
					self.makeMegamorphic()
					break
				else:
					temp = self.makeTarget(context)
					self.objects[cpaType] = temp
					changed = True
			else:
				temp = self.objects[cpaType]

			temp.updateSingleValue(obj)
		else:
			if changed: self.doNotify()



# TODO prevent over splitting?  All objects with the same qualifier should be grouped?
class ExactSplitConstraint(Splitter):
	def __init__(self, src):
		Splitter.__init__(self, src)
		self.objects = {}

	def localName(self):
		return 'exact_split_temp'

	def changed(self, context, node, diff):
		changed = False
		for obj in diff:
			if obj not in self.objects:
				temp = self.makeTarget(context)
				self.objects[obj] = temp
				changed = True
			else:
				temp = self.objects[obj]

			temp.updateSingleValue(obj)

		if changed: self.doNotify()
