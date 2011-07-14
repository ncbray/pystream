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

import util.canonical

Any  = util.canonical.Sentinel('<Any>')

class DoNotCareType(object):
	def isDoNotCare(self):
		return True
	def __repr__(self):
		return '<DoNotCare>'

DoNotCare = DoNotCareType()

# A canonical name for a CPAed parameter list.
class CPASignature(util.canonical.CanonicalObject):
	__slots__ = 'code', 'selfparam', 'params'

	def __init__(self, code, selfparam, params):
		params = tuple(params)

		# HACK - Sanity check.  Used for catching infinite loops in the analysis
		assert len(params) < 30, (code, params)

		self.code      = code
		self.selfparam = selfparam
		self.params    = params

		self.setCanonical(code, selfparam, params)

	def classification(self):
		return (self.code, self.numParams())

	# Is this signature more general than another signature?
	# Megamorphic and slop arguments are marked as "Any" which is
	# more general than a spesific type.
	def subsumes(self, other):
		if self.classification() == other.classification():
			subsume = False
			for sparam, oparam in zip(self.params, other.params):
				if sparam is Any and oparam is not Any:
					subsume = True
				elif sparam != oparam:
					return False
			return subsume
		else:
			return False

	def numParams(self):
		return len(self.params)

	def __repr__(self):
		return "%s(code=%s, self=%r, params=%r)" % (type(self).__name__, self.code.codeName(), self.selfparam, self.params)
