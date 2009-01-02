from . import base

class WildcardSchema(base.Schema):
	__slots__ = ()
	def __init__(self):
		pass

	def validate(self, args):
		pass

class TypeSchema(base.Schema):
	def __init__(self, type_):
		self.type_ = type_

	def validate(self, args):
		if not isinstance(args, self.type_):
			raise base.SchemaError, "Expected type %s, got %s." % (repr(self.type_), repr(type(args)))
		


class StructureSchema(base.Schema):
	__slots__ = 'fields', 'map'
	def __init__(self, *fields):
		self.fields = []
		self.map = {}
		
		for name, field in fields:
			self.__addField(name, field)

	def __addField(self, name, field):
		if name in self.map:
			raise base.SchemaError, "Structure has multiple definitions for name '%s'" % (name,)

		self.fields.append((name, field))
		self.map[name] = field

	def field(self, name):
		if name not in self.map:
			raise base.SchemaError, "Schema for structures has no field '%s'" % (name,)
		return self.map[name]

	def fieldnames(self):
		return self.map.keys()

	def validate(self, args):
		assert isinstance(args, tuple), args

		if len(args) != len(self.fields):
			raise base.SchemaError, "Structure has %d fields, but %d fields were given." % (len(self.fields), len(args))
		
		for (name, field), arg in zip(self.fields, args):
			field.validate(arg)
