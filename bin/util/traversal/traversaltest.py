from __init__ import *

def treeTest():
	### Test App ###
	class Node(object):
		def __init__(self, l, r):
			self.l = l
			self.r = r

		def children(self):
			# TODO what if the children mutate while traversing?
			return (self.l, self.r)

		def accept(self, visitor, *args):
			visitor.visitNode(self, *args)


	class Leaf(object):
		def __init__(self, value):
			self.value = value

		def children(self):
			return ()

		def accept(self, visitor, *args):
			visitor.visitLeaf(self, *args)




	class PrintTree(ConcreteVisitor):
		def __init__(self, state):
			self.state = state
		
		def visitNode(self, node):
			print (self.state.indent*'\t')+"+"
			self.state.indent += 1

		def visitLeaf(self, node):
			print (self.state.indent*'\t')+str(node.value)

	class Dedent(ConcreteVisitor):
		def __init__(self, state):
			self.state = state
		
		def visitNode(self, node):
			self.state.indent -= 1

		def visitLeaf(self, node):
			self.state.sum += node.value

	class PrintState(object):
		def __init__(self):
			self.indent = 0
			self.sum = 0

	def treePrinter():
		om = DefaultObjectModel()
		state = PrintState()
		visitor = DFS(PrintTree(state), Dedent(state))
		visitor.setObjectModel(om)
		return visitor


	class ReduceTree(ConcreteVisitor):
		def visitLeaf(self, node):
			return node

		def visitNode(self, node):
			if isinstance(node.l, Leaf) and isinstance(node.r, Leaf):
				node = Leaf(node.l.value+node.r.value)
				print "FOLD", node.value
				return node
			else:
				return node

	def treeFolder():
		om = DefaultObjectModel()
		visitor = BottomUp(ReduceTree())
		visitor.setObjectModel(om)
		return visitor



	tree = Node(Node(Node(Leaf(1), Leaf(2)), Leaf(3)), Node(Leaf(4), Leaf(5)))

	treePrinter().visit(tree, ())
	treeFolder().visit(tree, ())
	treePrinter().visit(tree, ())


def graphTest():
	# Bipartite graph model.  Iterates nodes and edges.
	class GraphObjectModel(ObjectModel):
		def __init__(self, G):
			self.G = G
			
		def children(self, node):
			if isinstance(node, tuple):
				return (node[1],)
			else:
				return [(node, child) for child in self.G[node]]

		def disbatch(self, visitor, node, args):
			if isinstance(node, tuple):
				return visitor.visitEdge(node[0], node[1], *args)
			else:
				return visitor.visitNode(node, *args)
	
	class DFSState(object):
		def __init__(self):
			self.uid = 0
			self.preorder 	= {}
			self.postorder 	= {}

		def pre(self, node):
			self.preorder[node] = self.uid
			self.uid += 1

		def post(self, node):
			self.postorder[node] = self.uid
			self.uid += 1


	class OnPre(ConcreteVisitor):
		def __init__(self, state):
			self.state = state

		def visitNode(self, node):
			self.state.pre(node)

		def visitEdge(self, src, dst):
			pass

	class OnPost(ConcreteVisitor):
		def __init__(self, state):
			self.state = state

		def visitNode(self, node):
			self.state.post(node)
			print node, (self.state.preorder[node], self.state.postorder[node])

		def visitEdge(self, src, dst):
			direction = 'forward' if dst in self.state.postorder else 'backward'
		
			print "Edge", src, dst, direction


	G = {0:[1], 1:[2], 2:[3], 3:[1]}

	state = DFSState()
	visitor = DFS(OnPre(state), OnPost(state))
	visitor.setObjectModel(GraphObjectModel(G))
	visitor.visit(0, ())

treeTest()
graphTest()