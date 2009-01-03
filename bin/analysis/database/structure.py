from . import base

import util.namedtuple

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
			raise base.SchemaError, "Expected type %r, got %r." % (self.type_, type(args))
		


class StructureSchema(base.Schema):
	__slots__ = 'fields', 'map', 'type_'
	def __init__(self, *fields):
		self.fields = []
		self.map = {}

		for name, field in fields:
			self.__addField(name, field)

		# HACK no typename, just 'structure'?
		names = [name for name, field in fields]
		self.type_ = util.namedtuple.namedtuple('structure', names)

	def missing(self):
		return self.type_(*[field.missing() for (name, field) in self.fields])

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


	def merge(self, *args):
		output = self.missing()
		for arg in args:
			self.validate(arg)
			output = self.type_(*[field.inplaceMerge(target, data) for (name, field), target, data in zip(self.fields, output, arg)])
		return output

	def inplaceMerge(self, *args):
		return self.merge(*args)
