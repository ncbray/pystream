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