from util.xform.traversal import allChildren, replaceAllChildren
from . simplify import simplify


class Rewriter(object):
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

	def processCode(self, code, replacements):
		if replacements:
			self.replacements = replacements
			self.replaced     = set()
			replaceAllChildren(self, code)
		return code

def rewriteAndSimplify(extractor, storeGraph, code, replace):
	if replace:
		Rewriter().processCode(code, replace)
		simplify(extractor, storeGraph, code)
	return code