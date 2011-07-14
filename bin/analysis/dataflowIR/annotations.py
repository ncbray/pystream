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

class CorrelatedAnnotation(object):
	__slots__ = 'flat', 'correlated'
	def __init__(self, flat, correlated):
		self.flat = flat
		self.correlated = correlated


class DataflowAnnotation(object):
	__slots__ = ()

	def rewrite(self, **kwds):
		# Make sure extraneous keywords were not given.
		for name in kwds.iterkeys():
			assert name in self.__slots__, name

		values = {}
		for name in self.__slots__:
			if name in kwds:
				value = kwds[name]
			else:
				value = getattr(self, name)
			values[name] = value

		return type(self)(**values)


class DataflowOpAnnotation(DataflowAnnotation):
	__slots__ = 'read', 'modify', 'allocate', 'mask'

	def __init__(self, read, modify, allocate, mask):
		self.read     = read
		self.modify   = modify
		self.allocate = allocate
		self.mask     = mask


class DataflowSlotAnnotation(DataflowAnnotation):
	__slots__ = 'values', 'unique'

	def __init__(self, values, unique):
		self.values = values
		self.unique = unique


class DataflowObjectAnnotation(DataflowAnnotation):
	__slots__ = 'preexisting', 'unique', 'mask', 'final'

	def __init__(self, preexisting, unique, mask, final):
		self.preexisting = preexisting
		self.unique      = unique
		self.mask        = mask
		self.final       = final

	def __repr__(self):
		return "%s(preexisting=%r, unique=%r, mask=%r, final=%r)" % (type(self).__name__, self.preexisting, self.unique, self.mask, self.final)
