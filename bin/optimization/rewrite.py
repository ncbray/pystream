from util.traversal import allChildren, replaceAllChildren
import optimization.simplify


class Rewriter(object):
	def __init__(self, replacements):
		self.replacements = replacements
		self.replaced = set()

	def __call__(self, node):
		if isinstance(node, list):
			# Unhashable, can't check for replacement
			return allChildren(self, node)

		# Prevent stupid recursion, where the replacement
		# contains the original.
		if node in self.replaced:
			return node

		if node in self.replacements:
			oldnode = node
			self.replaced.add(oldnode)
			node = allChildren(self, self.replacements[node])
			self.replaced.remove(oldnode)
		else:
			node = allChildren(self, node)

		return node

	def processCode(self, code):
		replaceAllChildren(self, code)
		return code

def rewriteTerm(term, replace):
	if replace:
		term = Rewriter(replace)(term)
	return term

def rewriteAndSimplify(compiler, code, replace):
	if replace:
		Rewriter(replace).processCode(code)
		optimization.simplify.evaluateCode(compiler, code)
	return code