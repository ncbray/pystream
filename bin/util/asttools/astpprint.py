import sys
import cStringIO
from . metaast import ASTNode

class ASTPrettyPrinter(object):
	def __init__(self, out=None, eol='\n'):
		if out is None: out = sys.stdout
		self.out = out
		self.eol = eol

	def isLeaf(self, node):
		if isinstance(node, ASTNode):
			return node.__leaf__
		else:
			return not isinstance(node, (list, tuple))

	def handleContainer(self, node, label, tabs):
		if isinstance(node, list):
			l, r = '[', ']'
		else:
			l, r = '(', ')'

		trivial = not node or all([self.isLeaf(child) for child in node])

		if trivial:
			contents = ", ".join([repr(child) for child in node])
			self.out.write("%s%s%s%s%s%s" % (tabs, label, l, contents, r, self.eol))
		else:
			self.out.write("%s%s%s%s" % (tabs, label, l, self.eol))
			for i, child in enumerate(node):
				self(child, '%d = '%i, tabs+'\t')
			self.out.write("%s%s%s" % (tabs, r, self.eol))

	def __call__(self, node, label, tabs, first=False):
		if isinstance(node, (list, tuple)):
			# Container
			self.handleContainer(node, label, tabs)
		elif self.isLeaf(node) or (not first and getattr(node, '__shared__', False)):
			# Leaf
			self.out.write("%s%s%r%s" % (tabs, label, node, self.eol))
		else:
			# Normal AST node
			self.out.write("%s%s%s%s" % (tabs, label, type(node).__name__, self.eol))
			for name, child in node.fields():
				self(child, '%s = ' % name, tabs+'\t')

	def process(self, node):
		self(node, '', '', first=True)

def pprint(node, out=None, eol='\n'):
	ASTPrettyPrinter(out=out, eol=eol).process(node)

def toString(node, eol='\n'):
	out = cStringIO.StringIO()
	pprint(node, out=out, eol=eol)
	return out.getvalue()
