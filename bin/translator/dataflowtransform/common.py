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

from language.python import ast
from util.asttools import annotation

def nameForField(compiler, field):
	name = field.name.pyobj

	# Create a somewhat meaningful name for this local
	if field.type == 'Attribute':
		descriptor = compiler.slots.reverse[name]
		originalName = descriptor.__name__
	elif field.type == 'Array':
		originalName = 'array_%d' % name
	elif field.type == 'LowLevel':
		originalName = name

	else:
		assert False, field

	return originalName

def localForFieldSlot(compiler, code, example, group=None):
	field = example.slotName

	originalName = nameForField(compiler, field)

	# Create a conservative annotation
	if group is None:
		group = (example,)

	refs = set()
	for field in group:
		refs.update(field)
	refsAnnotation = annotationFromValues(code, refs)

	# Create the new local
	lcl = ast.Local(originalName)
	lcl.rewriteAnnotation(references=refsAnnotation)
	return lcl


def emptyAnnotation(code):
	value = ()
	return annotation.ContextualAnnotation(value, tuple([value for _context in code.annotation.contexts]))

def annotationFromValues(code, values):
	values = annotation.annotationSet(values)
	return annotation.ContextualAnnotation(values, tuple([values for _context in code.annotation.contexts]))
