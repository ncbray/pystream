from util.typedispatch import *
import sys

from language.python import ast

class ASTPrettyPrinter(StrictTypeDispatcher):
	@dispatch(ast.Local, ast.Existing, str, int, float, type(None))
	def visitLeaf(self, node, label, tabs):
		self.out.write("%s%s%r\n" % (tabs, label, node))

	@dispatch(ast.Code)
	def visitShared(self, node, label, tabs):
		self.out.write("%s%s(%s, ...)\n" % (tabs, type(node).__name__, node.name))

	@dispatch(list)
	def visitList(self, node, label, tabs):
		if node:
			self.out.write("%s%s[\n" % (tabs, label))
			for i, child in enumerate(node):
				self(child, '%d = '%i, tabs+'\t')
			self.out.write("%s]\n" % tabs)
		else:
			self.out.write("%s%s[]\n" % (tabs, label))

	@dispatch(tuple)
	def visitTuple(self, node, label, tabs):
		if node:
			self.out.write("%s%s(\n" % (tabs, label))
			for i, child in enumerate(node):
				self(child, '%d = '%i, tabs+'\t')
			self.out.write("%s)\n" % tabs)
		else:
			self.out.write("%s%s()\n" % (tabs, label))

	@defaultdispatch
	def default(self, node, label, tabs):
		self.out.write("%s%s%s\n" % (tabs, label, type(node).__name__))
		for name, child in node.fields():
			self(child, '%s = ' % name, tabs+'\t')

	def process(self, node, out=None):
		if out is None:
			out = sys.stdout
		self.out = out
		self.default(node, '', '')

def pprint(node, out=None):
	ASTPrettyPrinter().process(node, out)
