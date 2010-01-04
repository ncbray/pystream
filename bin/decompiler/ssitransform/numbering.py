from util.typedispatch import *
from language.python import ast

def contains(parent, child):
	return parent[0] < child[0] and parent[1] > child[1]

class NumberAST(TypeDispatcher):
	def __init__(self):
		TypeDispatcher.__init__(self)
		self.uid = 0
		self.numbering = {}

	@dispatch(str, int, float, type(None))
	def visitLeaf(self, node):
		return node

	@defaultdispatch
	def default(self, node):
		pre = self.uid
		self.uid += 1

		node.visitChildren(self)

		post = self.uid
		self.uid += 1

		assert not node in self.numbering, node
		self.numbering[node] = (pre, post)

	@dispatch(ast.Local, ast.Cell, ast.Existing)
	def visitRef(self, node):
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

	def process(self, node):
		assert node.__shared__, node
		node.visitChildrenForced(self)
