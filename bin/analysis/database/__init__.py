class Schema(object):
	__slots__ = ()
	def __call__(self):
		return self.instance()
	

	def missing(self):
		return self.instance()

class FieldSchema(Schema):
	__slots__ = 'name'
	def __init__(self, name):
		self.name = name

class StructureSchema(Schema):
	def __init__(self, name, fields):
		self.name   = name
		self.fields = fields
		self.map = {}
		for field in fields:
			assert not name in self.map
			self.map[name] = field
			
class TupleSetSchema(Schema):
	def __init__(self, valueschema):
		self.valueschema = valueschema

	def instance(self):
		return TupleSet(self)

class TupleSet(object):
	def __init__(self, schema):
		assert isinstance(schema, TupleSetSchema), type(schema)
		self.schema = schema
		self.data   = set()

##	def add(self, *args):
##
##	def itermap(self, *fields):


class TupleMapSchema(Schema):
	def __init__(self, keyschema, valueschema):
		self.keyschema   = keyschema
		self.valueschema = valueschema

	def instance(self):
		return TupleMap(self)
	

class TupleMap(object):
	def __init__(self, schema):
		assert isinstance(schema, TupleMapSchema), type(schema)
		self.schema = schema
		self.data = {}

	def get(self, *vargs):
		self.schema.validate(vargs)
		
		if not vargs in self.data:
			result = self.schema.missing()
			self.data[vargs] = result
		else:
			result = self.data[vargs]

		return result


	def __iter__(self):
		for key, value in self.data.iteritems():
			yield key+(value,)
