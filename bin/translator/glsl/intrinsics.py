from optimization.termrewrite import *

from tests.full import vec

intrinsicTypes = frozenset([vec.vec2, vec.vec3, vec.vec4, vec.mat2, vec.mat3, vec.mat4])

def typeCallRewrite(node):
	if isAnalysis(node.args[0], intrinsicTypes):
		return True

	return None

def maxRewrite(node):
	return True

def addRewrite(node):
	return True

def subRewrite(node):
	return True

def mulRewrite(node):
	return True

def divRewrite(node):
	return True

def dotRewrite(node):
	return True

def swizzleRewrite(node):
	return True

def makeIntrinsicRewriter(extractor):
	rewriter = DirectCallRewriter(extractor)
	rewriter.addRewrite('type__call__', typeCallRewrite)
	rewriter.addRewrite('max_stub', maxRewrite)

	# UGLY call may be gone after cloning?

	rewriter.attribute(vec.vec2, '__add__', addRewrite)
	rewriter.attribute(vec.vec3, '__add__', addRewrite)
	rewriter.attribute(vec.vec4, '__add__', addRewrite)

	rewriter.attribute(vec.vec2, '__sub__', subRewrite)
	rewriter.attribute(vec.vec3, '__sub__', subRewrite)
	rewriter.attribute(vec.vec4, '__sub__', subRewrite)

	#rewriter.attribute(vec.mat2, '__add__', addRewrite)
	#rewriter.attribute(vec.mat3, '__add__', addRewrite)
	#rewriter.attribute(vec.mat4, '__add__', addRewrite)

	rewriter.attribute(vec.vec2, '__mul__', mulRewrite)
	rewriter.attribute(vec.vec3, '__mul__', mulRewrite)
	rewriter.attribute(vec.vec4, '__mul__', mulRewrite)

	rewriter.attribute(vec.mat2, '__mul__', mulRewrite)
	rewriter.attribute(vec.mat3, '__mul__', mulRewrite)
	rewriter.attribute(vec.mat4, '__mul__', mulRewrite)

	rewriter.attribute(vec.vec2, '__div__', divRewrite)
	rewriter.attribute(vec.vec3, '__div__', divRewrite)
	rewriter.attribute(vec.vec4, '__div__', divRewrite)

	rewriter.attribute(vec.vec2, 'dot', dotRewrite)
	rewriter.attribute(vec.vec3, 'dot', dotRewrite)
	rewriter.attribute(vec.vec4, 'dot', dotRewrite)

	rewriter.function(vec.vec4.__dict__['xyz'].fget, swizzleRewrite)


	return rewriter