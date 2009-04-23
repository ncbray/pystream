from optimization.termrewrite import *

from tests.full import vec

intrinsicTypes = frozenset([vec.vec2, vec.vec3, vec.vec4, vec.mat2, vec.mat3, vec.mat4])

def typeCallRewrite(node):
	if isAnalysis(node.args[0], intrinsicTypes):
		return True

	return None

def makeIntrinsicRewriter(exports):
	rewriter = DirectCallRewriter(exports)
	rewriter.addRewrite('type__call__', typeCallRewrite)
	return rewriter