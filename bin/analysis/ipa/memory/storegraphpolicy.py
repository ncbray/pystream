from .. constraints import qualifiers

class DefaultStoreGraphPolicy(object):
	def __init__(self, storeGraph):
		self.storeGraph = storeGraph

	def fieldValues(self, analysis, slot):
		obj, fieldtype, fieldname = slot.name

		sgregion = self.storeGraph.regionHint
		sgobj = sgregion.object(obj.xtype)

		canonicalField = analysis.canonical.fieldName(fieldtype, fieldname)
		sgfield = sgobj.field(canonicalField, sgregion)

		xtypes = sgfield.refs

		return [analysis.objectName(ref, qualifiers.HZ) for ref in xtypes], False
