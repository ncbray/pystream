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

#@PydevCodeAnalysisIgnore

from __future__ import absolute_import

from .. stubcollector import stubgenerator

import _random
import time

@stubgenerator
def makeRandomStubs(collector):
	llfunc        = collector.llfunc
	export        = collector.export
	replaceAttr   = collector.replaceAttr
	fold          = collector.fold
	attachPtr     = collector.attachPtr


	@attachPtr(_random.Random, 'random')
	@llfunc(descriptive=True)
	def random_stub(self):
		return allocate(float)

	# HACK where should this be declared?
	# A function, not a method, so no "self"
	@attachPtr(time.clock)
	@llfunc(descriptive=True)
	def clock_stub():
		return allocate(float)
