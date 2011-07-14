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

from functools import wraps

def conditional(cond, func):
	if cond:
		return func
	else:
		def passthroughTemp(func):
			return func
		return passthroughTemp


# Decorator that starts a debugger if an exception is thrown
def debugOnFailiure(func):
	@wraps(func)
	def debugOnFailiureDecorator(*args, **kargs):
		try:
			return func(*args, **kargs)
		except:
			import traceback
			traceback.print_exc()

			try:
				import pdb
				pdb.post_mortem()
			except Exception, e:
				print "Cannot start debugger: " + str(e)

			raise
	return debugOnFailiureDecorator


def conditionalDebugOnFailiure(cond):
	return conditional(cond, debugOnFailiure)
