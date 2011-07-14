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

from util.asttools.origin import originString

class TranslationError(Exception):
	def __init__(self, code, node, reason):
		self.code   = code
		self.node   = node
		self.reason = reason

		trace = '\n'.join([originString(origin) for origin in node.annotation.origin])

		Exception.__init__(self, "\n\n".join([reason, repr(code), trace, repr(node)]))

class TemporaryLimitation(TranslationError):
	pass
