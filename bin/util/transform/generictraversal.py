from base import *

class All(Transformer):
	__metaclass__ = astnode
	__fields__    = 's'
	__types__     = {'s':Transformer}
		
	def __call__(self, node, env):
		assert node != fail, repr(self)

		# Early out
		if isinstance(node, LeafTypes):
			return node

		newchildren = []
		transformed = False

		for child in children(node):
			newchild = self.s(child, env)			
			if child != newchild:
				transformed = True
			newchildren.append(newchild)
		
		if transformed:
			node = reconstruct(node, newchildren)

		return node

class Congruence(Transformer):
	__metaclass__ = astnode
	__fields__    = 'type_', 'strategies'
	__types__     = {'type_':type, 'strategies':list}
	

	def __call__(self, node, env):
		assert node != fail, repr(self)

		# Types must match.
		if not type(node) is self.type_:
			return doFail()

		# This should probabally be checked statically.
		assert len(node.children()) == len(self.strategies)

		newchildren = []
		transformed = False
		
		for child, s in zip(children(node), self.strategies):
			newchild = s(child, env)
			if child != newchild: transformed = True
			newchildren.append(newchild)

		if transformed:
			node = reconstruct(node, newchildren)
		return node
