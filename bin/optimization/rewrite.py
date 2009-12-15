import optimization.simplify
from util.typedispatch import *

class Rewriter(TypeDispatcher):
	def __init__(self, replacements):
		TypeDispatcher.__init__(self)
		self.replacements = replacements
		self.replaced = set()

	@dispatch(str, int, type(None))
	def visitLeaf(self, node):
		if node in self.replaced:
			return node
		
		if node in self.replacements:
			oldnode = node
			self.replaced.add(oldnode)
			node = self(self.replacements[node])
			self.replaced.remove(oldnode)
		
		return node

	@dispatch(list, tuple)
	def visitContainer(self, node):
		# AST nodes may sometimes be replaced with containers,
		# so unlike most transformations, this will get called.
		return [self(child) for child in node]

	@defaultdispatch
	def visitNode(self, node):
		# Prevent stupid recursion, where the replacement
		# contains the original.
		if node in self.replaced:
			return node

		if node in self.replacements:
			oldnode = node
			self.replaced.add(oldnode)
			node = self(self.replacements[node])
			self.replaced.remove(oldnode)
		else:
			node = node.rewriteChildren(self)

		return node

	def processCode(self, code):
		code.replaceChildren(self)
		return code

def rewriteTerm(term, replace):
	if replace:
		term = Rewriter(replace)(term)
	return term

def rewrite(compiler, code, replace):
	if replace:
		Rewriter(replace).processCode(code)
	return code

def rewriteAndSimplify(compiler, code, replace):
	if replace:
		Rewriter(replace).processCode(code)
		optimization.simplify.evaluateCode(compiler, code)
	return code
