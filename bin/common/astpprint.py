from util.typedispatch import *
import sys

from language.python import ast

import cStringIO

trivialTypes = (ast.Local, ast.Existing, str, int, float, type(None))

class ASTPrettyPrinter(TypeDispatcher):
	def __init__(self, out=None, eol='\n'):
		if out is None: out = sys.stdout
		self.out = out
		self.eol = eol

	@dispatch(ast.Local, ast.Existing, str, int, float, type(None))
	def visitLeaf(self, node, label, tabs):
		self.out.write("%s%s%r%s" % (tabs, label, node, self.eol))

	@dispatch(ast.Code)
	def visitShared(self, node, label, tabs):
		self.out.write("%s%s(%s, ...)%s" % (tabs, type(node).__name__, node.name, self.eol))

	@dispatch(list)
	def visitList(self, node, label, tabs):
		trivial = not node or all([isinstance(child, trivialTypes) for child in node])

		if trivial:
			contents = ", ".join([repr(child) for child in node])
			self.out.write("%s%s[%s]%s" % (tabs, label, contents, self.eol))
		else:
			self.out.write("%s%s[%s" % (tabs, label, self.eol))
			for i, child in enumerate(node):
				self(child, '%d = '%i, tabs+'\t')
			self.out.write("%s]%s" % (tabs, self.eol))

	@dispatch(tuple)
	def visitTuple(self, node, label, tabs):
		trivial = not node or all([isinstance(child, trivialTypes) for child in node])

		if trivial:
			contents = ", ".join([repr(child) for child in node])
			self.out.write("%s%s(%s)%s" % (tabs, label, contents, self.eol))
		else:
			self.out.write("%s%s(%s" % (tabs, label, self.eol))
			for i, child in enumerate(node):
				self(child, '%d = '%i, tabs+'\t')
			self.out.write("%s)%s" % (tabs, self.eol))

	@defaultdispatch
	def default(self, node, label, tabs):
		self.out.write("%s%s%s%s" % (tabs, label, type(node).__name__, self.eol))
		for name, child in node.fields():
			self(child, '%s = ' % name, tabs+'\t')

	def process(self, node):
		self.default(node, '', '')

def pprint(node, out=None, eol='\n'):
	ASTPrettyPrinter(out=out, eol=eol).process(node)

def toString(node, eol='\n'):
	out = cStringIO.StringIO()
	pprint(node, out=out, eol=eol)
	return out.getvalue()