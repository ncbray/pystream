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

def doNothing(node):
	pass

class CFGDFS(object):
	def __init__(self, pre=doNothing, post=doNothing):
		self.pre  = pre
		self.post = post
		self.processed = set()

	def process(self, node):
		if node not in self.processed:
			self.processed.add(node)

			self.pre(node)

			for child in node.forward():
				self.process(child)

			self.post(node)
