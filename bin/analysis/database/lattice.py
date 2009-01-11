import util.compressedset
from . import base


class SetSchema(base.Schema):
	__slots = ()
	def validate(self, arg):
		if util.compressedset.validate(arg):
			return True
		else:
			raise base.SchemaError, "Expected compressed set, got %s" % type(arg).__name__

	def missing(self):
		return None

	def copy(self, original):
		return util.compressedset.copy(original)


class SetUnionSchema(SetSchema):
	__slots = ()

	def merge(self, *args):
		return util.compressedset.union(*args)

	def inplaceMerge(self, *args):
		return util.compressedset.inplaceUnion(*args)

setUnionSchema = SetUnionSchema()


class SetIntersectionSchema(SetSchema):
	__slots = ()

	def merge(self, *args):
		return util.compressedset.intersection(*args)
	
	def inplaceMerge(self, *args):
		return util.compressedset.inplaceIntersection(*args)

setIntersectionSchema = SetIntersectionSchema()
