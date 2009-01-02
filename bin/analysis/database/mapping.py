from . import base

class MappingSchema(base.Schema):
	__slots__ = 'keyschema', 'valueschema'
	def __init__(self, keyschema, valueschema):
		self.keyschema   = keyschema
		self.valueschema = valueschema

	def instance(self):
		return Mapping(self)

	def missing(self):
		return self.instance()

	def validateKey(self, args):
		self.keyschema.validate(args)

	def validateValue(self, args):
		self.valueschema.validate(args)


	def merge(self, *args):
		target = self.missing()
		return self.inplaceMerge(target, *args)

	def inplaceMerge(self, target, *args):
		for arg in args:
			for key, value in arg:
				target.merge(key, value)
		return target

class Mapping(object):
	__slots__ = 'schema', 'data'
	def __init__(self, schema):
		assert isinstance(schema, MappingSchema), type(schema)
		self.schema = schema
		self.data = {}

	def __getitem__(self, key):
		self.schema.validateKey(key)
		
		if not key in self.data:
			result = self.schema.valueschema.missing()
			self.data[key] = result
		else:
			result = self.data[key]

		return result

	def __len__(self):
		return len(self.data)

	def __iter__(self):
		return self.data.iteritems()

	def forget(self):
		return self.schema.valueschema.merge(*self.data.values())

	def merge(self, key, values):
		self.data[key] = self.schema.valueschema.inplaceMerge(self[key], values)
