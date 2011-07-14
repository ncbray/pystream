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

from util.typedispatch import *
import analysis.dataflowIR.graph as graph

class LivenessKiller(TypeDispatcher):
	def __init__(self, live):
		self.live = live
		self.queue = []
		self.processed  = set()

	@dispatch(graph.LocalNode, graph.FieldNode, graph.PredicateNode)
	def handleSlot(self, node):
		if self.dead(node.use):
			node.use = None

	@dispatch(graph.ExistingNode)
	def handleExistingNode(self, node):
		node.uses = [use for use in node.uses if not self.dead(use)]

	@dispatch(graph.NullNode)
	def handleNullNode(self, node):
		node.uses = [use for use in node.uses if not self.dead(use)]

	@dispatch(graph.GenericOp)
	def handleGenericOp(self, node):
		if all(self.dead(lcl) for lcl in node.localModifies):
			node.localModifies = []

		# TODO turn dead modifies (heap and locals) into don't cares?

	@dispatch(graph.Entry)
	def handleEntry(self, node):
		modifies = {}
		for name, next in node.modifies.iteritems():
			if not self.dead(next): modifies[name] = next
		node.modifies = modifies

	@dispatch(graph.Exit)
	def handleExit(self, node):
		# A field that exists at the output may be dead for a number of reasons.
		# For example, if the field simply bridges the entry to the exit, it will be dead.
		reads = {}
		for name, prev in node.reads.iteritems():
			if not self.dead(prev): reads[name] = prev
		node.reads = reads

	@dispatch(graph.Split)
	def handleSplit(self, node):
		node.modifies = [m for m in node.modifies if not self.dead(m)]
		node.optimize()

	@dispatch(graph.Gate)
	def handleGate(self, node):
		pass

	@dispatch(graph.Merge)
	def handleMerge(self, node):
		if self.dead(node.modify):
			for read in node.reads:
				read.removeUse(node)

			if node.modify is not None:
				node.modify.removeDefn(node)

			node.reads = []
			node.modify = None

	def dead(self, node):
		return node is None or node not in self.live

	def mark(self, node):
		assert isinstance(node, graph.DataflowNode), node
		if node not in self.processed:
			self.processed.add(node)
			self.queue.append(node)

	def process(self, dataflow):
		self.mark(dataflow.entry)

		# Filter existing
		existing = {}
		for name, node in dataflow.existing.iteritems():
			if node in self.live:
				existing[name] = node
				self.mark(node)
		dataflow.existing = existing

		self.mark(dataflow.null)
		self.mark(dataflow.entryPredicate)

		# Process
		while self.queue:
			current = self.queue.pop()
			self(current)
			for next in current.forward():
				# Note: dead slots may hang around if they're written to by an op.
				# As such, we process dead slots to make sure any use they have is killed.
				if not self.dead(next) or isinstance(next, graph.SlotNode):
					self.mark(next)

class LivenessSearcher(TypeDispatcher):
	def __init__(self):
		self.queue = []
		self.live  = set()

	def mark(self, node):
		assert isinstance(node, graph.DataflowNode), node
		if node not in self.live:
			self.live.add(node)
			self.queue.append(node)

	def process(self, dataflow):
		self.mark(dataflow.exit)

		while self.queue:
			current = self.queue.pop()
			if current.isOp() and current.isExit():
				for prev in current.reverse():
					if prev.isField() and prev.defn.isEntry():
						pass # The field is simply passed through.
					else:
						self.mark(prev)
			else:
				for prev in current.reverse():
					self.mark(prev)

		return self.live


def evaluateDataflow(dataflow):
	live = LivenessSearcher().process(dataflow)
	LivenessKiller(live).process(dataflow)
