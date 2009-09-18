from optimization.termrewrite import *
from language.glsl import ast as glsl

from tests.full import vec
import random

constantTypes = frozenset([float, int, bool])
intrinsicTypes = frozenset([float, int, bool, vec.vec2, vec.vec3, vec.vec4, vec.mat2, vec.mat3, vec.mat4])

constantTypeNodes = {}
intrinsicTypeNodes = {}

typeComponents = {}
componentTypes = {}
componentTypeNodes = {}

fields = {}

referenceType = glsl.BuiltinType('ref')

for t in intrinsicTypes:
	intrinsicTypeNodes[t] = glsl.BuiltinType(t.__name__)
for t in constantTypes:
	constantTypeNodes[t] = intrinsicTypeNodes[t]

import util
def uniqueAttrName(type, name):
	return util.uniqueSlotName(type.__dict__[name])

def addName(type, name, fields):
	un = uniqueAttrName(type, name)
	fields[un] = name

def components(cls, ctype, cnum):
	key = ctype, cnum
	
	# HACK (float, 4) -> vec4 and mat2?  
	if key not in componentTypes:
		typeComponents[cls] = key
		componentTypes[key] = cls
		componentTypeNodes[key] = intrinsicTypeNodes[cls]

components(float, float, 1)

components(vec.vec2, float, 2)
addName(vec.vec2, 'x', fields)
addName(vec.vec2, 'y', fields)

components(vec.vec3, float, 3)
addName(vec.vec3, 'x', fields)
addName(vec.vec3, 'y', fields)
addName(vec.vec3, 'z', fields)

components(vec.vec4, float, 4)
addName(vec.vec4, 'x', fields)
addName(vec.vec4, 'y', fields)
addName(vec.vec4, 'z', fields)
addName(vec.vec4, 'w', fields)

components(vec.mat2, float, 4)
components(vec.mat3, float, 9)
components(vec.mat4, float, 16)

components(int, int, 1)
components(bool, bool, 1)

def isIntrinsicMemoryOp(node):
	return node.fieldtype == 'Attribute' and isinstance(node.name, ast.Existing) and node.name.object.pyobj in fields

def typeCallRewrite(self, node):
	if isSimpleCall(node) and isAnalysis(node.args[0], intrinsicTypes):
		if self is None:
			return True
		else:
			t = node.args[0].object.pyobj
			return glsl.Constructor(intrinsicTypeNodes[t], self(node.args[1:]))
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
		return glsl.UnaryPrefixOp('+', self(node.args[0]))

def negRewrite(self, node):
	if not hasNumArgs(node, 1): return

	if self is None:
		return True
	else:
		return glsl.UnaryPrefixOp('-', self(node.args[0]))

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