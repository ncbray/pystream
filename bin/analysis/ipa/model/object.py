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

from language.python import program
from .. constraints import node, qualifiers

from ..escape import objectescape

class Object(object):
	__slots__ = 'context', 'name', 'fields', 'flags', 'dirty'

	def __init__(self, context, name):
		self.context = context
		self.name    = name
		self.fields  = {}
		self.flags   = 0
		self.dirty   = False

		if name.qualifier is qualifiers.DN:
			self.flags |= objectescape.escapeParam
		elif name.qualifier is qualifiers.GLBL:
			self.flags |= objectescape.escapeGlobal

	def updateFlags(self, context, flags):
		diff = ~self.flags & flags
		if diff:
			self.flags |= diff
			if not self.dirty:
				self.dirty = True
				context.dirtyObject(self)

	def initDownwardField(self, slot, fieldtype, name):
		for invoke in self.context.invokeIn.itervalues():
			invoke.copyFieldFromSources(slot, self.name, fieldtype, name)

	def initExistingField(self, slot, fieldtype, fieldname):
		analysis  = self.context.analysis

		if fieldtype == 'LowLevel' and fieldname.pyobj == 'type':
			ao = analysis.existingPolicy.typeObject(analysis, self.name)
			values, null = [ao], False
		elif self.name.xtype.isExternal():
			values, null = analysis.externalPolicy.fieldValues(analysis, slot, self.name, fieldtype, fieldname)
		else:
			values, null = analysis.existingPolicy.fieldValues(analysis, slot, self.name, fieldtype, fieldname)

		if values: slot.updateValues(frozenset(values))
		if null: slot.markNull()

	def field(self, fieldType, name):
		assert isinstance(fieldType, str), fieldType
		assert isinstance(name, program.AbstractObject), name

		key = (fieldType, name)

		if key not in self.fields:
			result = node.ConstraintNode(self.context, (self.name, fieldType, name))
			self.fields[key] = result

			if self.context.external:
				self.initExistingField(result, fieldType, name)
			elif self.name.qualifier is qualifiers.GLBL:
				self.initExistingField(result, fieldType, name) # HACK unsound
			elif self.name.qualifier is qualifiers.DN:
				self.initDownwardField(result, fieldType, name)
			else:
				result.markNull()
		else:
			result = self.fields[key]

		return result
