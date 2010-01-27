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

	def initDownwardField(self, slot):
		for invoke in self.context.invokeIn.itervalues():
			invoke.copyFieldFromSources(slot)

	def initExistingField(self, slot):
		obj, fieldtype, fieldname = slot.name
		analysis  = self.context.analysis

		if fieldtype == 'LowLevel' and fieldname.pyobj == 'type':
			ao = analysis.existingPolicy.typeObject(analysis, obj)
			values, null = [ao], False
		elif obj.xtype.isExternal():
			values, null = analysis.externalPolicy.fieldValues(analysis, slot)
		else:
			values, null = analysis.existingPolicy.fieldValues(analysis, slot)

		if values: slot.updateValues(frozenset(values))
		if null: slot.markNull()

	def field(self, fieldType, name):
		assert isinstance(fieldType, str), fieldType
		assert isinstance(name, program.AbstractObject), name

		key = (fieldType, name)

		if key not in self.fields:
			result = node.ConstraintNode(self.context, (self.name, fieldType, name))
			self.fields[key] = result

			if self.name.qualifier is qualifiers.DN:
				self.initDownwardField(result)
			elif self.context.external:
				self.initExistingField(result)
			else:
				result.markNull()
		else:
			result = self.fields[key]

		return result
