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

class SchemaError(Exception):
	pass

class DatabaseError(Exception):
	pass

class Schema(object):
	"""
	Schema abstract base class.
	"""

	__slots__ = ()

	def __call__(self):
		return self.instance()

	def validateNoRaise(self, args):
		try:
			self.validate(args)
		except SchemaError:
			return False
		else:
			return True

	def merge(self, *args):
		target = self.missing()
		target, changed = self.inplaceMerge(target, *args)
		return target
