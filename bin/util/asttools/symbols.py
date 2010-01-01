from util.typedispatch import *

class SymbolBase(object):
	__slots__ = ()

class Symbol(SymbolBase):
	__slots__ = ('name',)
	def __init__(self, name):
		self.name = name

	def __repr__(self):
		return '{%s}' % self.name


class SymbolRewriter(TypeDispatcher):
	def __init__(self, lut):
		self.lut = lut

	@dispatch(Symbol)
	def visitSymbol(self, node):
		return self.lut.get(node.name, node)

	@dispatch(str, int, float, type(None))
	def visitLeaf(self, node):
		return node

	@defaultdispatch
	def default(self, node):
		return node.rewriteChildren(self)

	# Will not be invoked by traversal functions,
	# included so groups of nodes can be rewritten
	@dispatch(list)
	def visitList(self, node):
		return [self(child) for child in node]


def rewrite(template, **kargs):
	# TODO check that all arguments are used
	return SymbolRewriter(kargs)(template)
