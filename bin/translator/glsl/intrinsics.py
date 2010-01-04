from optimization.termrewrite import *
from language.glsl import ast as glsl

from shader import vec, sampler
import random

def _merge(*args):
	data = []
	for arg in args:
		data.extend(arg)
	return frozenset(data)

constantTypes = frozenset([float, int, bool])
vectorTypes   = frozenset([vec.vec2, vec.vec3, vec.vec4])
matrixTypes   = frozenset([vec.mat2, vec.mat3, vec.mat4])
samplerTypes  = frozenset([sampler.sampler2D])

intrinsicTypes = _merge(constantTypes, vectorTypes, matrixTypes, samplerTypes)

constantTypeNodes = {}
intrinsicTypeNodes = {}

typeComponents = {} # type -> (componentType, count)
componentTypes = {} # (componentType, count) -> type
componentTypeNodes = {}

fields = {}

referenceType = glsl.BuiltinType('ref')

for t in intrinsicTypes:
	intrinsicTypeNodes[t] = glsl.BuiltinType(t.__name__)
for t in constantTypes:
	constantTypeNodes[t] = intrinsicTypeNodes[t]

import util

initialized = False

def init(compiler):
	# Prevent multiple initializations
	global initialized
	if initialized: return
	initialized = True

	def uniqueAttrName(type, name):
		return compiler.slots.uniqueSlotName(type.__dict__[name])

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

	components(sampler.sampler2D, sampler.sampler2D, 1)


def isIntrinsicObject(obj):
	return obj.xtype.obj.pythonType() in intrinsicTypes

def isIntrinsicType(t):
	return t in intrinsicTypes

def isIntrinsicField(field):
	return field.type == 'Attribute' and field.name.pyobj in fields

def isIntrinsicSlot(slot):
	return isIntrinsicObject(slot.object) and isIntrinsicField(slot.slotName)


def isIntrinsicMemoryOp(node):
	return node.fieldtype == 'Attribute' and isinstance(node.name, ast.Existing) and node.name.object.pyobj in fields

def getSingleType(node):
	values = node.annotation.references.merged
	types = set([value.xtype.obj.pythonType() for value in values])
	if len(types) != 1: return None
	t = types.pop()
	return t

# Expand scalar arguments into vectors
def coerceArgs(self, arg0, arg1):
	arg0type = getSingleType(arg0)
	if arg0type is None: return None

	arg1type = getSingleType(arg1)
	if arg1type is None: return None

	arg0 = self(arg0)
	arg1 = self(arg1)

	if arg0type is arg1type:
		pass
	elif typeComponents[arg0type][0] is arg1type:
		# arg1 needs to be expanded
		arg1 = glsl.Constructor(intrinsicTypeNodes[arg0type], [arg1])
	elif typeComponents[arg1type][0] is arg0type:
		# arg0 needs to be expanded
		arg0 = glsl.Constructor(intrinsicTypeNodes[arg1type], [arg0])
	else:
		# error
		return None

	return [arg0, arg1]


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
		args = coerceArgs(self, *node.args)
		if args is None: return None
		return glsl.IntrinsicOp('max', args)

def minRewrite(self, node):
	if not hasNumArgs(node, 2): return

	if self is None:
		return True
	else:
		args = coerceArgs(self, *node.args)
		if args is None: return None
		return glsl.IntrinsicOp('min', args)

def addRewrite(self, node):
	if not hasNumArgs(node, 2): return

	if self is None:
		return True
	else:
		return glsl.BinaryOp(self(node.args[0]), '+', self(node.args[1]))

def raddRewrite(self, node):
	if not hasNumArgs(node, 2): return

	if self is None:
		return True
	else:
		return glsl.BinaryOp(self(node.args[1]), '+', self(node.args[0]))

def subRewrite(self, node):
	if not hasNumArgs(node, 2): return

	if self is None:
		return True
	else:
		return glsl.BinaryOp(self(node.args[0]), '-', self(node.args[1]))

def rsubRewrite(self, node):
	if not hasNumArgs(node, 2): return

	if self is None:
		return True
	else:
		return glsl.BinaryOp(self(node.args[1]), '-', self(node.args[0]))

def mulRewrite(self, node):
	if not hasNumArgs(node, 2): return

	if self is None:
		return True
	else:
		return glsl.BinaryOp(self(node.args[0]), '*', self(node.args[1]))

def rmulRewrite(self, node):
	if not hasNumArgs(node, 2): return

	if self is None:
		return True
	else:
		return glsl.BinaryOp(self(node.args[1]), '*', self(node.args[0]))

def divRewrite(self, node):
	if not hasNumArgs(node, 2): return

	if self is None:
		return True
	else:
		return glsl.BinaryOp(self(node.args[0]), '/', self(node.args[1]))

def rdivRewrite(self, node):
	if not hasNumArgs(node, 2): return

	if self is None:
		return True
	else:
		return glsl.BinaryOp(self(node.args[1]), '/', self(node.args[0]))

def powRewrite(self, node):
	if not hasNumArgs(node, 2): return

	if self is None:
		return True
	else:
		args = coerceArgs(self, *node.args)
		if args is None: return None
		return glsl.IntrinsicOp('pow', args)

def rpowRewrite(self, node):
	if not hasNumArgs(node, 2): return

	if self is None:
		return True
	else:
		args = coerceArgs(self, *node.args)
		if args is None: return None
		return glsl.IntrinsicOp('pow', [args[1], args[0]])

def dotRewrite(self, node):
	if not hasNumArgs(node, 2): return

	if self is None:
		return True
	else:
		args = coerceArgs(self, *node.args)
		if args is None: return None
		return glsl.IntrinsicOp('dot', args)

def crossRewrite(self, node):
	if not hasNumArgs(node, 2): return

	if self is None:
		return True
	else:
		args = coerceArgs(self, *node.args)
		if args is None: return None
		return glsl.IntrinsicOp('cross', args)

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

def distanceRewrite(self, node):
	if not hasNumArgs(node, 2): return

	if self is None:
		return True
	else:
		args = coerceArgs(self, *node.args)
		if args is None: return None
		return glsl.IntrinsicOp('distance', args)

def mixRewrite(self, node):
	if not hasNumArgs(node, 3): return

	if self is None:
		return True
	else:
		args = coerceArgs(self, node.args[0], node.args[1])
		if args is None: return None
		args.append(self(node.args[2]))
		return glsl.IntrinsicOp('mix', args)

def reflectRewrite(self, node):
	if not hasNumArgs(node, 2): return

	if self is None:
		return True
	else:
		args = coerceArgs(self, *node.args)
		if args is None: return None
		return glsl.IntrinsicOp('reflect', args)

def refractRewrite(self, node):
	if not hasNumArgs(node, 3): return

	if self is None:
		return True
	else:
		args = coerceArgs(self, node.args[0], node.args[1])
		if args is None: return None
		args.append(self(node.args[2]))
		return glsl.IntrinsicOp('refract', args)

def expRewrite(self, node):
	if not hasNumArgs(node, 1): return

	if self is None:
		return True
	else:
		return glsl.IntrinsicOp('exp', self(node.args))

def logRewrite(self, node):
	if not hasNumArgs(node, 1): return

	if self is None:
		return True
	else:
		return glsl.IntrinsicOp('log', self(node.args))

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

def floatSubRewrite(self, node):
	if not hasNumArgs(node, 2): return

	if self is None:
		return True
	else:
		return glsl.BinaryOp(self(node.args[0]), '-', self(node.args[1]))

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
		args = coerceArgs(self, *node.args)
		if args is None: return None
		return glsl.IntrinsicOp('pow', args)


def samplerTextureRewrite(self, node):
	if not hasNumArgs(node, 2): return

	if self is None:
		return True
	else:
		return glsl.IntrinsicOp('texture', [self(arg) for arg in node.args])


def makeIntrinsicRewriter(extractor):
	init(extractor.compiler)

	rewriter = DirectCallRewriter(extractor)

	rewriter.addRewrite('prim_float_add', floatAddRewrite)
	rewriter.addRewrite('prim_float_sub', floatSubRewrite)
	rewriter.addRewrite('prim_float_mul', floatMulRewrite)
	rewriter.addRewrite('prim_float_div', floatDivRewrite)
	rewriter.addRewrite('prim_float_pow', floatPowRewrite)
	rewriter.addRewrite('prim_float_pos', posRewrite)
	rewriter.addRewrite('prim_float_neg', negRewrite)


	rewriter.addRewrite('type__call__', typeCallRewrite)
	rewriter.addRewrite('max_stub', maxRewrite)
	rewriter.addRewrite('min_stub', minRewrite)

	rewriter.addRewrite('math_exp', expRewrite)
	rewriter.addRewrite('math_log', expRewrite)


	fvecs = (vec.vec2, vec.vec3, vec.vec4)

	for v in fvecs: rewriter.attribute(v, '__add__', addRewrite)
	for v in fvecs: rewriter.attribute(v, '__radd__', raddRewrite)
	for v in fvecs: rewriter.attribute(v, '__sub__', subRewrite)
	for v in fvecs: rewriter.attribute(v, '__rsub__', rsubRewrite)

	#rewriter.attribute(vec.mat2, '__add__', addRewrite)
	#rewriter.attribute(vec.mat3, '__add__', addRewrite)
	#rewriter.attribute(vec.mat4, '__add__', addRewrite)

	for v in fvecs: rewriter.attribute(v, '__mul__', mulRewrite)
	for v in fvecs: rewriter.attribute(v, '__rmul__', rmulRewrite)

	for m in (vec.mat2, vec.mat3, vec.mat4):
		rewriter.attribute(m, '__mul__', mulRewrite)
		#rewriter.attribute(m, '__rmul__', rmulRewrite)

	for v in fvecs: rewriter.attribute(v, '__div__', divRewrite)
	for v in fvecs: rewriter.attribute(v, '__rdiv__', rdivRewrite)
	for v in fvecs: rewriter.attribute(v, '__pow__', powRewrite)
	for v in fvecs: rewriter.attribute(v, '__rpow__', rpowRewrite)

	for v in fvecs: rewriter.attribute(v, 'min', minRewrite)
	for v in fvecs: rewriter.attribute(v, 'max', maxRewrite)

	for v in fvecs: rewriter.attribute(v, 'dot', dotRewrite)
	for v in fvecs: rewriter.attribute(v, 'length', lengthRewrite)
	for v in fvecs: rewriter.attribute(v, 'normalize', normalizeRewrite)
	for v in fvecs: rewriter.attribute(v, 'distance', distanceRewrite)
	for v in fvecs: rewriter.attribute(v, 'mix', mixRewrite)
	for v in fvecs: rewriter.attribute(v, 'reflect', reflectRewrite)
	for v in fvecs: rewriter.attribute(v, 'refract', refractRewrite)
	for v in fvecs: rewriter.attribute(v, 'exp', expRewrite)
	for v in fvecs: rewriter.attribute(v, 'log', logRewrite)


	for v in fvecs: rewriter.attribute(v, '__pos__', posRewrite)
	for v in fvecs: rewriter.attribute(v, '__neg__', negRewrite)
	for v in fvecs: rewriter.attribute(v, '__abs__', absRewrite)

	rewriter.attribute(vec.vec3, 'cross', crossRewrite)

	rewriter.function(vec.vec4.__dict__['xyz'].fget, swizzleRewrite)

	# HACK
	rewriter.attribute(random._random.Random, 'random', randomRewrite)

	rewriter.addRewrite('texture', samplerTextureRewrite)

	return rewriter
