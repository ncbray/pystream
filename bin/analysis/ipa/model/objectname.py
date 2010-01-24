from analysis.storegraph import extendedtypes

class ObjectName(object):
	__slots__ = 'xtype', 'qualifier'
	def __init__(self, xtype, qualifier):
		assert isinstance(xtype, extendedtypes.ExtendedType), xtype
		self.xtype = xtype
		self.qualifier = qualifier

	def __repr__(self):
		return "ao(%r, %s/%d)" % (self.xtype, self.qualifier, id(self))

	def cpaType(self):
		return self.xtype.cpaType()
