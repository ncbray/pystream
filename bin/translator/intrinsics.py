from optimization.termrewrite import *
from language.glsl import ast as glsl

from shader import vec, sampler, function
import random

def _merge(*args):
	data = []
	for arg in args:
		data.extend(arg)
	return frozenset(data)

constantTypes = frozenset([float, int, bool])
vectorTypes   = frozenset([vec.vec2, vec.vec3, vec.vec4])
matrixTypes   = frozenset([vec.mat2, vec.mat3, vec.mat4])
samplerTypes  = frozenset([sampler.sampler2D, sampler.samplerCube])

intrinsicTypes = _merge(constantTypes, vectorTypes, matrixTypes, samplerTypes)

constantTypeNodes = {}
intrinsicTypeNodes = {}
intrinsicToType = {}

typeComponents = {} # type -> (componentType, count)
componentTypes = {} # (componentType, count) -> type
componentTypeNodes = {}

fields = {}

byteAlignment = {}
byteSize = {}

referenceType = glsl.BuiltinType('ref')

for t in intrinsicTypes:
	bt = glsl.BuiltinType(t.__name__)
	intrinsicTypeNodes[t] = bt
	intrinsicToType[bt] = t

for t in constantTypes:
	constantTypeNodes[t] = intrinsicTypeNodes[t]

import util

initialized = False

def basicAlignment(ctype, count):
	if count == 3: count = 4
	return count*4

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

	def scalarComponents(cls, ctype, cnum):
		byteAlignment[cls] = basicAlignment(ctype, cnum)
		byteSize[cls] = cnum*4

		components(cls, ctype, cnum)

	def matrixComponents(cls, ctype, col, row):
		byteAlignment[cls] = 4*4
		byteSize[cls] = basicAlignment(ctype, row)*col
		components(cls, ctype, col*row)

	scalarComponents(float, float, 1)

	scalarComponents(vec.vec2, float, 2)
	addName(vec.vec2, 'x', fields)
	addName(vec.vec2, 'y', fields)

	scalarComponents(vec.vec3, float, 3)
	addName(vec.vec3, 'x', fields)
	addName(vec.vec3, 'y', fields)
	addName(vec.vec3, 'z', fields)

	scalarComponents(vec.vec4, float, 4)
	addName(vec.vec4, 'x', fields)
	addName(vec.vec4, 'y', fields)
	addName(vec.vec4, 'z', fields)
	addName(vec.vec4, 'w', fields)

	matrixComponents(vec.mat2, float, 2, 2)
	addName(vec.mat2, 'm00', fields)
	addName(vec.mat2, 'm01', fields)
	addName(vec.mat2, 'm10', fields)
	addName(vec.mat2, 'm11', fields)

	matrixComponents(vec.mat3, float, 3, 3)
	addName(vec.mat3, 'm00', fields)
	addName(vec.mat3, 'm01', fields)
	addName(vec.mat3, 'm02', fields)
	addName(vec.mat3, 'm10', fields)
	addName(vec.mat3, 'm11', fields)
	addName(vec.mat3, 'm12', fields)
	addName(vec.mat3, 'm20', fields)
	addName(vec.mat3, 'm21', fields)
	addName(vec.mat3, 'm22', fields)

	matrixComponents(vec.mat4, float, 4, 4)
	addName(vec.mat4, 'm00', fields)
	addName(vec.mat4, 'm01', fields)
	addName(vec.mat4, 'm02', fields)
	addName(vec.mat4, 'm03', fields)
	addName(vec.mat4, 'm10', fields)
	addName(vec.mat4, 'm11', fields)
	addName(vec.mat4, 'm12', fields)
	addName(vec.mat4, 'm13', fields)
	addName(vec.mat4, 'm20', fields)
	addName(vec.mat4, 'm21', fields)
	addName(vec.mat4, 'm22', fields)
	addName(vec.mat4, 'm23', fields)
	addName(vec.mat4, 'm30', fields)
	addName(vec.mat4, 'm31', fields)
	addName(vec.mat4, 'm32', fields)
	addName(vec.mat4, 'm33', fields)

	scalarComponents(int, int, 1)
	scalarComponents(bool, bool, 1)

	for st in samplerTypes:
		scalarComponents(st, st, 1)


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

def smoothstepRewrite(self, node):
	if not hasNumArgs(node, 3): return

	if self is None:
		return True
	else:
		return glsl.IntrinsicOp('smoothstep', self(node.args))


def clampRewrite(self, node):
	if not hasNumArgs(node, 3): return

	if self is None:
		return True
	else:
		return glsl.IntrinsicOp('clamp', self(node.args))


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

### Compare Ops ###

def eqRewrite(self, node):
	if not hasNumArgs(node, 2): return

	if self is None:
		return True
	else:
		return glsl.BinaryOp(self(node.args[0]), '==', self(node.args[1]))

def neRewrite(self, node):
	if not hasNumArgs(node, 2): return

	if self is None:
		return True
	else:
		return glsl.BinaryOp(self(node.args[0]), '!=', self(node.args[1]))

def gtRewrite(self, node):
	if not hasNumArgs(node, 2): return

	if self is None:
		return True
	else:
		return glsl.BinaryOp(self(node.args[0]), '>', self(node.args[1]))

def geRewrite(self, node):
	if not hasNumArgs(node, 2): return

	if self is None:
		return True
	else:
		return glsl.BinaryOp(self(node.args[0]), '>=', self(node.args[1]))

def ltRewrite(self, node):
	if not hasNumArgs(node, 2): return

	if self is None:
		return True
	else:
		return glsl.BinaryOp(self(node.args[0]), '<', self(node.args[1]))

def leRewrite(self, node):
	if not hasNumArgs(node, 2): return

	if self is None:
		return True
	else:
		return glsl.BinaryOp(self(node.args[0]), '<=', self(node.args[1]))

def samplerTextureRewrite(self, node):
	if hasNumArgs(node, 2) or hasNumArgs(node, 3):
		if self is None:
			return True
		else:
			return glsl.IntrinsicOp('texture', [self(arg) for arg in node.args])
	else:
		return

def samplerTextureLodRewrite(self, node):
	if not hasNumArgs(node, 3): return

	if self is None:
		return True
	else:
		return glsl.IntrinsicOp('textureLod', [self(arg) for arg in node.args])


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

	rewriter.addRewrite('prim_float_eq', eqRewrite)
	rewriter.addRewrite('prim_float_ne', neRewrite)
	rewriter.addRewrite('prim_float_gt', gtRewrite)
	rewriter.addRewrite('prim_float_ge', geRewrite)
	rewriter.addRewrite('prim_float_lt', ltRewrite)
	rewriter.addRewrite('prim_float_le', leRewrite)



	rewriter.addRewrite('prim_int_add', floatAddRewrite)
	rewriter.addRewrite('prim_int_sub', floatSubRewrite)
	rewriter.addRewrite('prim_int_mul', floatMulRewrite)
	rewriter.addRewrite('prim_int_div', floatDivRewrite)
	rewriter.addRewrite('prim_int_pow', floatPowRewrite)
	rewriter.addRewrite('prim_int_pos', posRewrite)
	rewriter.addRewrite('prim_int_neg', negRewrite)

	rewriter.addRewrite('prim_int_eq', eqRewrite)
	rewriter.addRewrite('prim_int_ne', neRewrite)
	rewriter.addRewrite('prim_int_gt', gtRewrite)
	rewriter.addRewrite('prim_int_ge', geRewrite)
	rewriter.addRewrite('prim_int_lt', ltRewrite)
	rewriter.addRewrite('prim_int_le', leRewrite)

	rewriter.addRewrite('type__call__', typeCallRewrite)
	rewriter.addRewrite('max_stub', maxRewrite)
	rewriter.addRewrite('min_stub', minRewrite)

	rewriter.addRewrite('math_exp', expRewrite)
	rewriter.addRewrite('math_log', logRewrite)

	rewriter.function(function.clamp, clampRewrite)
	rewriter.function(function.smoothstep, smoothstepRewrite)


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
	rewriter.function(vec.vec4.__dict__['xy'].fget, swizzleRewrite)
	rewriter.function(vec.vec3.__dict__['xy'].fget, swizzleRewrite)

	# HACK
	rewriter.attribute(random._random.Random, 'random', randomRewrite)

	rewriter.addRewrite('texture', samplerTextureRewrite)
	rewriter.addRewrite('textureLod', samplerTextureLodRewrite)

	return rewriter
