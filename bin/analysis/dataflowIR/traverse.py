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

class DFSTraversal(object):
	def __init__(self, callback):
		self.callback = callback
		self.processed = set()

	def mark(self, node):
		if node not in self.enqueued:
			self.enqueued.add(node)
			self.queue.append(node)

	def handleNode(self, node):
		if node not in self.processed:
			self.processed.add(node)

			self.callback(node)

			for child in node.forward():
				self.handleNode(child)

	def process(self, dataflow):
		self.handleNode(dataflow.entry)
		for node in dataflow.existing.itervalues():
			self.handleNode(node)
		self.handleNode(dataflow.null)
		self.handleNode(dataflow.entryPredicate)

def dfs(dataflow, callback):
	dfs = DFSTraversal(callback)
	dfs.process(dataflow)
