# Copyright 2011 Nicholas Bray
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from . import base

class TupleSetSchema(base.Schema):
	def __init__(self, valueschema):
		self.valueschema = valueschema

	def instance(self):
		return TupleSet(self)

	def missing(self):
		return self.instance()

	def validate(self, args):
		self.valueschema.validate(args)

	def inplaceMerge(self, target, *args):
		oldLen = len(target)
		for arg in args:
			for value in arg:
				target.add(*value)
		newLen = len(target)
		return target, oldLen != newLen


class TupleSet(object):
	def __init__(self, schema):
		assert isinstance(schema, TupleSetSchema), type(schema)
		self.schema = schema
		self.data   = set()

	def __len__(self):
		return len(self.data)

	def __iter__(self):
		return iter(self.data)

	def add(self, *args):
		self.schema.validate(args)
		self.data.add(args)

	def remove(self, *args):
		self.schema.validate(args)
		if not args in self.data:
			raise base.DatabaseError, "Cannot remove tuple %r from database, as the tuple is not in the database" % (args,)
		self.data.remove(args)
