from language.python import program
from .. constraints import node, qualifiers

class Object(object):
	__slots__ = 'context', 'name', 'fields'

	def __init__(self, context, name):
		self.context = context
		self.name   = name
		self.fields = {}

	def initDownwardField(self, slot):
		for invoke in self.context.invokeIn.itervalues():
			invoke.copyFieldFromSources(slot)

	def initExistingField(self, slot):

		obj, fieldtype, fieldname = slot.name

		xtype = obj.xtype
		obj = xtype.obj

		assert isinstance(obj, program.AbstractObject), obj

		extractor = self.context.analysis.compiler.extractor

		extractor.ensureLoaded(obj)

		canonical = self.context.analysis.canonical

		filled = False

		if fieldtype == 'LowLevel' and fieldname.pyobj == 'type':
			# Type pointer
			self.updateExternal(slot, canonical.existingType(obj.type))
			filled = True
		elif xtype.isExternal():
			# User-specified memory image
			storeGraph = self.context.analysis.storeGraph
			sgobj = storeGraph.regionHint.object(xtype)
			canonicalField = canonical.fieldName(fieldtype, fieldname)
			sgfield = sgobj.field(canonicalField, storeGraph.regionHint)
			xtypes = sgfield.refs
			for ref in xtypes:
				self.updateExternal(slot, ref)
				filled = True
		else:
			# TODO
			#if isinstance(obj.pyobj, list):
			#	return set([canonical.existingType(t) for t in obj.array.itervalues()])

			# Extracted from memory
			if isinstance(obj, program.Object):
				if fieldtype == 'LowLevel':
					subdict = obj.lowlevel
				elif fieldtype == 'Attribute':
					subdict = obj.slot
				elif fieldtype == 'Array':
					subdict = obj.array
				elif fieldtype == 'Dictionary':
					subdict = obj.dictionary
				else:
					assert False, fieldtype

				if fieldname in subdict:
					self.updateExternal(slot, canonical.existingType(subdict[fieldname]))
					filled = True

		if not filled: slot.markNull()


	def updateExternal(self, slot, xtype):
		if xtype.isExternal():
			qualifier=qualifiers.HZ
		else:
			qualifier=qualifiers.GLBL

		ao = self.context.analysis.objectName(xtype, qualifier)
		slot.updateSingleValue(ao)

		if False:
			print "external"
			print slot
			print ao


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
