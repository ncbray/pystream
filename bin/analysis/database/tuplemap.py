from . import base

class TupleMapSchema(base.Schema):
	__slots__ = 'keyschema', 'valueschema'
	def __init__(self, keyschema, valueschema):
		self.keyschema   = keyschema
		self.valueschema = valueschema

	def instance(self):
		return TupleMap(self)

	def missing(self):
		return self.instance()


	def validateKey(self, args):
		self.keyschema.validate(args)

	def validateValue(self, args):
		self.valueschema.validate(args)


class TupleMap(object):
	__slots__ = 'schema', 'data'
	def __init__(self, schema):
		assert isinstance(schema, TupleMapSchema), type(schema)
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
		return self.schema.valueschema.merge(self.data.itervalues())
