from util.typedispatch import *
from language.python import ast

import util.graphalgorithim.dominator

from . dataflow import ForwardDataflow

# For debugging
from util.xmloutput import XMLOutput

class MakeForwardDominance(object):
	def printDebug(self, tree, head):
		f = XMLOutput(open('temp.html', 'w'))
		f.begin('ul')

		def printNode(f, node):
			if not isinstance(node, tuple):
				f.begin('li')
				f.write(str(node))
				f.begin('ul')

			children = tree.get(node, ())

			for child in children:
				printNode(f, child)

			if not isinstance(node, tuple):
				f.end('ul')
				f.end('li')

		printNode(f, head)

		f.end('ul')
		f.close()

	def number(self, node):
		if node in self.processed: return
		self.processed.add(node)

		self.pre[node] = self.uid
		self.uid += 1

		for next in self.G.get(node, ()):
			self.number(next)

		self.dom[node] = (self.pre[node], self.uid)
		self.uid += 1

	def processCode(self, code):
		self.uid  = 0
		self.pre  = {}
		self.dom = {}

		self.processed = set()

		fdf = ForwardDataflow()

		self.G = fdf.processCode(code)
		head = fdf.entry[code]

		tree, idoms = util.graphalgorithim.dominator.dominatorTree(self.G, head)

		#self.printDebug(tree, head)

		self.G = tree
		self.number(head)

		return self.dom
