from util.visitor import StandardVisitor

def contains(parent, child):
	return parent[0] < child[0] and parent[1] > child[1]

class NumberAST(StandardVisitor):
	def __init__(self):
		self.uid = 0
		self.numbering = {}


	def visitstr(self, node):
		return node

	def visitint(self, node):
		return node

	def visitfloat(self, node):
		return node

	def visitNoneType(self, node):
		return node

	def visitlist(self, node):
		for child in node:
			self.visit(child)			

	def visittuple(self, node):
		for child in node:
			self.visit(child)
			
	def default(self, node):
		pre = self.uid
		self.uid += 1
		

		for child in node.children():
			self.visit(child)

		post = self.uid
		self.uid += 1


		assert not node in self.numbering, node
		self.numbering[node] = (pre, post)


		#print node, self.numbering[node]

	def visitLocal(self, node):
		self.handleShared(node)

	def visitCell(self, node):
		self.handleShared(node)

	def visitExisting(self, node):
		self.handleShared(node)
		
	
	def handleShared(self, node):
		pre = self.uid
		self.uid += 1

		post = self.uid
		self.uid += 1


		if node in self.numbering:
			pre = min(pre, self.numbering[node][0])
			post = max(post, self.numbering[node][1])
			
		self.numbering[node] = (pre, post)
