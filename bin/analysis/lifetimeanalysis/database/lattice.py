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


class SetSchema(base.Schema):
	__slots = ()
	def validate(self, arg):
		if isinstance(arg, (set, type(None))):
			return True
		else:
			raise base.SchemaError, "Expected set, got %s" % type(arg).__name__

	def missing(self):
		return None

	def copy(self, original):
		if original is None:
			return None
		else:
			return set(original)


class SetUnionSchema(SetSchema):
	__slots = ()

	def merge(self, *args):
		current = set()
		for arg in args:
			if arg is None: continue
			current.update(arg)

		if not current:
			return None

		return current

	def inplaceMerge(self, *args):
		current = args[0]

		if not current:
			current = set()
			oldLen  = 0
		else:
			oldLen = len(current)

		for arg in args[1:]:
			if arg is None: continue
			current.update(arg)

		if not current:
			return None, False

		newLen = len(current)

		return current, newLen != oldLen

setUnionSchema = SetUnionSchema()


class SetIntersectionSchema(SetSchema):
	__slots = ()

	def merge(self, *args):
		current = self.copy(args[0])

		if not current:
			return None

		for arg in args[1:]:
			if arg is None:
				current.clear()
				return current

			current.intersection_update(arg)

		if not current:
			current = None

		return current

	def inplaceMerge(self, *args):
		current = args[0]

		if not current:
			return None, False

		oldLen = len(current)

		for arg in args[1:]:
			if arg is None:
				current.clear()
				return current, oldLen != 0

			current.intersection_update(arg)

		changed = oldLen != len(current)

		if not current:
			current = None

		return current, changed

setIntersectionSchema = SetIntersectionSchema()
