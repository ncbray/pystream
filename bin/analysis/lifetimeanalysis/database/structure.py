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

import collections

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

	def instance(self):
		raise base.SchemaError, "Cannot directly create instances of types."

	def missing(self):
		return self.instance()

class CallbackSchema(base.Schema):
	def __init__(self, validator):
		self.validator = validator

	def validate(self, args):
		if not self.validator(args):
			raise base.SchemaError, "Callback did not validate %r." % (type(args))

	def instance(self):
		raise base.SchemaError, "Cannot directly create instances of callback schemas."

	def missing(self):
		return self.instance()

class StructureSchema(base.Schema):
	__slots__ = 'fields', 'map', 'type_'
	def __init__(self, *fields):
		self.fields = []
		self.map = {}

		for name, field in fields:
			self.__addField(name, field)

		# HACK no typename, just 'structure'?
		names = [name for name, field in fields]
		self.type_ = collections.namedtuple('structure', names)

	def instance(self):
		raise base.SchemaError, "Cannot directly create instances of structures."

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



	def inplaceMerge(self, target, *args):
		self.validate(target)
		for arg in args: self.validate(arg)

		accum = []

		changed = False
		for (name, fieldSchema), targetfield, argfields in zip(self.fields, target, zip(*args)):
			result, fieldChanged = fieldSchema.inplaceMerge(targetfield, *argfields)
			accum.append(result)
			changed |= fieldChanged

		output = self.type_(*accum)
		return output, changed

	def merge(self, *args):
		for arg in args: self.validate(arg)

		accum = []

		for (name, fieldSchema), argfields in zip(self.fields, zip(*args)):
			result = fieldSchema.merge(*argfields)
			accum.append(result)

		output = self.type_(*accum)
		return output
