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

from util.asttools.annotation import Annotation

class ObjectAnnotation(Annotation):
	__slots__ = 'preexisting', 'unique', 'final', 'uniform', 'input'

	def __init__(self, preexisting, unique, final, uniform, input):
		self.preexisting = preexisting
		self.unique      = unique
		self.final       = final
		self.uniform     = uniform
		self.input       = input

class FieldAnnotation(Annotation):
	__slots__ = 'unique',

	def __init__(self, unique):
		self.unique = unique

emptyFieldAnnotation  = FieldAnnotation(False)
emptyObjectAnnotation = ObjectAnnotation(False, False, False, False, False)
