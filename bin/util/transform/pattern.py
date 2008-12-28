from base import *
from programIR.base.metaast import Symbol, children, reconstruct, LeafTypes

# TODO allow strategies inside patterns.
# Note s => t

# TODO what about AST nodes with hidden children?

def match(p, n, env):
	if isinstance(p, Symbol):
		
		exists, value = env.contains(p.name)
		if exists:
			match(value, n, env)
		else:
			env.bind(p.name, n)
	elif isinstance(p, LeafTypes):
		if not p == n: return doFail()
	else:
		# Types must match
		if type(p) != type(n): return doFail()


		pchildren, nchildren = children(p), children(n)

		# Must have same number of children.  (A problem for lists and tuples.)
		if len(pchildren) != len(nchildren):
			return doFail()

		# Children must match.
		for pc, nc in zip(pchildren, nchildren):
			match(pc, nc, env)

	return True

def build(p, env):
	if isinstance(p, Symbol):
		return env.read(p.name)
	else:
		return reconstruct(p, [build(child, env) for child in children(p)])

class Match(Transformer):
	__metaclass__ = astnode
	__fields__    = 'p'

	def __call__(self, node, env):
		match(self.p, node, env)
		return node

class Build(Transformer):
	__metaclass__ = astnode
	__fields__    = 'p'

	def __call__(self, node, env):
		return build(self.p, env)
	
