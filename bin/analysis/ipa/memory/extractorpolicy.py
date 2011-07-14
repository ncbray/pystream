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

from language.python import program
from .. constraints import qualifiers

class ExtractorPolicy(object):
	def __init__(self, extractor):
		self.extractor = extractor

	def fieldValues(self, analysis, slot, ao, fieldtype, fieldname):
		obj = ao.xtype.obj

		self.extractor.ensureLoaded(obj)

		# TODO
		#if isinstance(obj.pyobj, list):
		#	return set([canonical.existingType(t) for t in obj.array.itervalues()])

		# Extracted from memory
		if isinstance(obj, program.Object):
			d = obj.getDict(fieldtype)

			if fieldname in d:
				xtype = analysis.canonical.existingType(d[fieldname])
				ao = analysis.objectName(xtype, qualifiers.GLBL)
				return [ao], False

		return [], True

	def typeObject(self, analysis, obj):
		# Get type pointer
		exobj = obj.xtype.obj
		self.extractor.ensureLoaded(exobj)
		xtype = analysis.canonical.existingType(exobj.type)

		ao = analysis.objectName(xtype, obj.qualifier) # TODO is this good enough for the qualifier?
		return ao
