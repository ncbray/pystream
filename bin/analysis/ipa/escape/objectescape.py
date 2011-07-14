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

### Flags ###

escapeReturn = 0x01
escapeParam  = 0x02
escapeGlobal = 0x04

nameToEnum = {
			'escapeReturn':escapeReturn,
			'escapeParam' :escapeParam,
			'escapeGlobal':escapeGlobal,
			}

escapes = escapeReturn | escapeParam | escapeGlobal

enumToName = {}
for name, enum in nameToEnum.iteritems():
	enumToName[enum] = name

def repr(flags):
	parts = []

	for enum, name in enumToName.iteritems():
		if flags & enum:
			parts.append(name)
			flags &= ~enum

	if flags:
		parts.append('???')

	if parts:
		return "|".join(parts)
	else:
		return 'empty'


### Analysis ###

def markSlot(context, slot, flags):
	region = context.region
	for name in slot.values:
		region.object(name).updateFlags(context, flags)

def propagateObjectFlags(context, obj):
	flags = obj.flags & escapes
	for slot in obj.fields.itervalues():
		markSlot(context, slot, flags)

# Mark all objects reachable from upward contexts
def process(context):
	# Escape flags may persist between iterations
	# Make these marked objects consistent

	# The objects dictionary may change during processing, so create a filtered copy
	roots = []
	region = context.region
	for obj in region.objects.itervalues():
		if obj.flags & escapes:
			roots.append(obj)

	for obj in roots:
		if not obj.dirty:
			propagateObjectFlags(context, obj)

	# Mark returned objects
	for param in context.returns:
		markSlot(context, param, escapeReturn)

	# Process the data flow
	context.processObjects(propagateObjectFlags)
