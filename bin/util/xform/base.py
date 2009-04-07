from language.base.metaast import children, reconstruct

class TransformFailiure(Exception):
	pass

def fail(node):
	raise TransformFailiure

def identity(node):
	return node
