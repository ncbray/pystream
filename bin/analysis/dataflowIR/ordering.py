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

from . import graph

class OrderSearcher(object):
	def __init__(self):
		self.queue = []
		self.enqueued = set()
		self.preorder = {}
		self.uid = 0

		self.order = []

	def mark(self, node):
		if node not in self.enqueued:
			self.enqueued.add(node)
			self.queue.append(node)

	def handleNode(self, node):
		if node not in self.preorder:
			self.preorder[node] = self.uid
			self.uid += 1

			self.queue.append(node)

			for child in node.forward():
				self.mark(child)
		else:
			postorder = self.uid
			self.uid += 1

			forward = (self.preorder[node], postorder)

			if isinstance(node, graph.OpNode):
				self.order.append(node)

	def process(self, dataflow):
		self.mark(dataflow.entry)
		for node in dataflow.existing.itervalues():
			self.mark(node)
		self.mark(dataflow.null)
		self.mark(dataflow.entryPredicate)

		while self.queue:
			self.handleNode(self.queue.pop())

		self.order.reverse()
		return self.order

def evaluateDataflow(dataflow):
	searcher = OrderSearcher()
	return searcher.process(dataflow)
