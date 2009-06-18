from optimization.termrewrite import *
from language.glsl import ast as glsl

from tests.full import vec
import random

intrinsicTypes = frozenset([float, int, bool, vec.vec2, vec.vec3, vec.vec4, vec.mat2, vec.mat3, vec.mat4])

import util
def uniqueAttrName(type, name):
	return util.uniqueSlotName(type.__dict__[name])

def addName(type, name, fields):
	un = uniqueAttrName(type, name)
	fields[un] = name

fields = {}
addName(vec.vec2, 'x', fields)
addName(vec.vec2, 'y', fields)

addName(vec.vec3, 'x', fields)
addName(vec.vec3, 'y', fields)
addName(vec.vec3, 'z', fields)

addName(vec.vec4, 'x', fields)
addName(vec.vec4, 'y', fields)
addName(vec.vec4, 'z', fields)
addName(vec.vec4, 'w', fields)


def typeCallRewrite(self, node):
	if isSimpleCall(node) and isAnalysis(node.args[0], intrinsicTypes):
		if self is None:
			return True
		else:
			name = node.args[0].object.pyobj.__name__
			return glsl.Constructor(glsl.BuiltinType(name), self(node.args[1:]))
	return None

def maxRewrite(self, node):
	if not hasNumArgs(node, 2): return

	if self is None:
		return True
	else:
		return glsl.IntrinsicOp('max', self(node.args))

def addRewrite(self, node):
	if not hasNumArgs(node, 2): return

	if self is None:
		return True
	else:
		return glsl.BinaryOp(self(node.args[0]), '+', self(node.args[1]))

def subRewrite(self, node):
	if not hasNumArgs(node, 2): return

	if self is None:
		return True
	else:
		return glsl.BinaryOp(self(node.args[0]), '-', self(node.args[1]))

def mulRewrite(self, node):
	if not hasNumArgs(node, 2): return

	if self is None:
		return True
	else:
		return glsl.BinaryOp(self(node.args[0]), '*', self(node.args[1]))

def divRewrite(self, node):
	if not hasNumArgs(node, 2): return

	if self is None:
		return True
	else:
		return glsl.BinaryOp(self(node.args[0]), '/', self(node.args[1]))

def dotRewrite(self, node):
	if not hasNumArgs(node, 2): return

	if self is None:
		return True
	else:
		return glsl.IntrinsicOp('dot', self(node.args))

def lengthRewrite(self, node):
	if not hasNumArgs(node, 1): return

	if self is None:
		return True
	else:
		return glsl.IntrinsicOp('length', self(node.args))

def normalizeRewrite(self, node):
	if not hasNumArgs(node, 1): return

	if self is None:
		return True
	else:
		return glsl.IntrinsicOp('normalize', self(node.args))

def posRewrite(self, node):
	if not hasNumArgs(node, 1): return

	if self is None:
		return True
	else:
		return glsl.UnaryPrefixOp('+', node.args[0])

def negRewrite(self, node):
	if not hasNumArgs(node, 1): return

	if self is None:
		return True
	else:
		return glsl.UnaryPrefixOp('-', node.args[0])

def absRewrite(self, node):
	if not hasNumArgs(node, 1): return

	if self is None:
		return True
	else:
		return glsl.IntrinsicOp('abs', self(node.args))

def swizzleRewrite(self, node):
	if not hasNumArgs(node, 1): return

	if self is None:
		return True
	else:
		name = node.code.annotation.origin.name
		return glsl.Load(self(node.args[0]), name)

def randomRewrite(self, node):
	if self is None:
		return True
	else:
		return glsl.IntrinsicOp('random', [])

def floatAddRewrite(self, node):
	if not hasNumArgs(node, 2): return

	if self is None:
		return True
	else:
		return glsl.BinaryOp(self(node.args[0]), '+', self(node.args[1]))

def floatMulRewrite(self, node):
	if not hasNumArgs(node, 2): return

	if self is None:
		return True
	else:
		return glsl.BinaryOp(self(node.args[0]), '*', self(node.args[1]))

def floatDivRewrite(self, node):
	if not hasNumArgs(node, 2): return

	if self is None:
		return True
	else:
		return glsl.BinaryOp(self(node.args[0]), '/', self(node.args[1]))

def floatPowRewrite(self, node):
	if not hasNumArgs(node, 2): return

	if self is None:
		return True
	else:
		return glsl.IntrinsicOp('pow', self(node.args))

def makeIntrinsicRewriter(extractor):
	rewriter = DirectCallRewriter(extractor)

	rewriter.addRewrite('prim_float_add', floatAddRewrite)
	rewriter.addRewrite('prim_float_mul', floatMulRewrite)
	rewriter.addRewrite('prim_float_div', floatDivRewrite)
	rewriter.addRewrite('prim_float_pow', floatPowRewrite)


	rewriter.addRewrite('type__call__', typeCallRewrite)
	rewriter.addRewrite('max_stub', maxRewrite)

	fvecs = (vec.vec2, vec.vec3, vec.vec4)

	for v in fvecs: rewriter.attribute(v, '__add__', addRewrite)
	for v in fvecs: rewriter.attribute(v, '__sub__', subRewrite)

	#rewriter.attribute(vec.mat2, '__add__', addRewrite)
	#rewriter.attribute(vec.mat3, '__add__', addRewrite)
	#rewriter.attribute(vec.mat4, '__add__', addRewrite)

	for v in fvecs: rewriter.attribute(v, '__mul__', mulRewrite)

	rewriter.attribute(vec.mat2, '__mul__', mulRewrite)
	rewriter.attribute(vec.mat3, '__mul__', mulRewrite)
	rewriter.attribute(vec.mat4, '__mul__', mulRewrite)

	for v in fvecs: rewriter.attribute(v, '__div__', divRewrite)
	for v in fvecs: rewriter.attribute(v, 'dot', dotRewrite)
	for v in fvecs: rewriter.attribute(v, 'length', lengthRewrite)
	for v in fvecs: rewriter.attribute(v, 'normalize', normalizeRewrite)

	for v in fvecs: rewriter.attribute(v, '__pos__', posRewrite)
	for v in fvecs: rewriter.attribute(v, '__neg__', negRewrite)
	for v in fvecs: rewriter.attribute(v, '__abs__', absRewrite)


	rewriter.function(vec.vec4.__dict__['xyz'].fget, swizzleRewrite)

	# HACK
	rewriter.attribute(random._random.Random, 'random', randomRewrite)

	return rewriter