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
