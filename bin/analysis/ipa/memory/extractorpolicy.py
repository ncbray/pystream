from language.python import program
from .. constraints import qualifiers

class ExtractorPolicy(object):
	def __init__(self, extractor):
		self.extractor = extractor

	def fieldValues(self, analysis, slot):
		ao, fieldtype, fieldname = slot.name
		obj = ao.xtype.obj

		self.extractor.ensureLoaded(obj)

		# TODO
		#if isinstance(obj.pyobj, list):
		#	return set([canonical.existingType(t) for t in obj.array.itervalues()])

		# Extracted from memory
		if isinstance(obj, program.Object):
			d = obj.getDict(fieldtype)

			if fieldname in d:
				xtype = analysis.canonical.existingType(d[fieldname])
				ao = analysis.objectName(xtype, qualifiers.GLBL)
				return [ao], False

		return [], True

	def typeObject(self, analysis, obj):
		# Get type pointer
		exobj = obj.xtype.obj
		self.extractor.ensureLoaded(exobj)
		xtype = analysis.canonical.existingType(exobj.type)

		ao = analysis.objectName(xtype, obj.qualifier) # TODO is this good enough for the qualifier?
		return ao
