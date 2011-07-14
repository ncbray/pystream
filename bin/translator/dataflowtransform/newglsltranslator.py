# Copyright 2011 Nicholas Bray
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from util.typedispatch import *
from language.python import ast
from language.glsl import ast as glsl
import language.glsl.tools

from translator import intrinsics
from translator.exceptions import TemporaryLimitation

from language.glsl import codegen


def makeRef(mode, t, name=None):
	bt = intrinsics.intrinsicTypeNodes[t]

	if mode is output:
		return glsl.Output(glsl.OutputDecl(None, False, False, False, bt, name))
	elif mode is uniform:
		return glsl.Uniform(glsl.UniformDecl(False, bt, name, None))
	elif mode is input:
		return glsl.Input(glsl.InputDecl(None, False, False, bt, name))
	elif mode is local:
		return glsl.Local(bt, name)
	else:
		assert False, mode

class SlotImpl(object):
	def __init__(self, subpool):
		self.subpool = subpool

class IntrinsicCopyImpl(SlotImpl):
	def __init__(self, subpool):
		SlotImpl.__init__(self, subpool)

	def makeRef(self, prefix):
		return CopyRef(self, makeRef(local, self.subpool.t, "%s_%s" % (prefix, self.subpool.t.__name__)))

class IntrinsicSingletonImpl(SlotImpl):
	def __init__(self, subpool):
		SlotImpl.__init__(self, subpool)

		if subpool.uniform:
			assert not subpool.input
			assert not subpool.allocated
			mode = uniform
		elif subpool.input:
			assert not subpool.allocated
			mode = input
		else:
			mode = local

		self.ref = makeRef(mode, subpool.t, 'singleton')

		self.refobj = SingletonRef(self)

	def makeRef(self, prefix):
		return self.refobj

class CopyRef(object):
	def __init__(self, impl, ref):
		self.impl = impl
		self.ref = ref

	def get(self):
		return self.ref

	def set(self, expr):
		return glsl.Assign(expr, self.ref)

	def assignTo(self, other):
		if self is not other:
			return other.set(self.get())
		else:
			return None

class SingletonRef(object):
	def __init__(self, impl):
		self.impl = impl

	def get(self):
		return self.impl.ref

	def set(self, expr):
		return glsl.Assign(expr, self.impl.ref)

	def assignTo(self, other):
		if self is not other:
			return other.set(self.get())
		else:
			return None

class RewriterWrapper(TypeDispatcher):
	def __init__(self, translator):
		TypeDispatcher.__init__(self)
		self.translator = translator

	@dispatch(ast.Local)
	def visitLocal(self, node):
		slotref = self.translator(node)
		return slotref.intrinsicRef(node.annotation.references.merged)

	@dispatch(ast.Existing)
	def visitExisting(self, node):
		return self.translator(node)

	@dispatch(list, tuple)
	def visitContainer(self, node):
		return [self(child) for child in node]

uniform = "UNIFORM"
local   = "LOCAL"
input   = "INPUT"
output  = "OUTPUT"

class StructureInfo(object):
	def __init__(self, translator, slot, poolInfo, mode, builtin):
		self.slot     = slot
		self.poolInfo = poolInfo
		self.mode     = mode
		self.builtin  = builtin

		prefix = translator.uniqueNameForSlot(slot, mode)

		if len(self.poolInfo.types) > 1:
			self.typeField = self.makeField(int, "%s_%s" % (prefix, 'type'))
		else:
			self.typeField = None

#		self.intrinsics = {}
#		for t in self.poolInfo.types:
#			if intrinsics.isIntrinsicType(t):
#				self.intrinsics[t] = self.makeField(t, "%s_%s" % (prefix, t.__name__))

		self.subpools = {}
		for name, subpool in poolInfo.lut.subpools.iteritems():
			impl = translator.subpoolInfo(subpool)
			self.subpools[name] = impl.makeRef(prefix)

	def makeField(self, t, name):
		bt = intrinsics.intrinsicTypeNodes[t]

		if self.mode is output:
			if self.builtin:
				# TODO check type?
				return glsl.Output(self.builtin)

			return glsl.Output(glsl.OutputDecl(None, False, False, False, bt, name))
		elif self.mode is uniform:
			if self.builtin:
				# TODO check type?
				return glsl.Uniform(self.builtin)

			return glsl.Uniform(glsl.UniformDecl(False, bt, name, None))
		elif self.mode is input:
			if self.builtin:
				# TODO check type?
				return glsl.Input(self.builtin)

			return glsl.Input(glsl.InputDecl(None, False, False, bt, name))
		elif self.mode is local:
			return glsl.Local(bt, name)
		else:
			assert False, self.mode

	def refTypes(self, refs):
		return set([ref.xtype.obj.pythonType() for ref in refs])

	def refType(self, refs):
		types = self.refTypes(refs)
		assert len(types) == 1
		return types.pop()

	def intrinsicRef(self, refs):
		assert not self.mode is output
		t = self.refType(refs)
		return self.intrinsicTypeRef(t)

	def intrinsicTypeRef(self, t):
		return self.subpools[t].get()

	def assignIntrinsic(self, analysis, refs, expr):
		assert self.mode is not input and self.mode is not uniform

		t = self.refType(refs)

		if self.typeField: analysis.initType(t, self.typeField)

		analysis.emit(self.subpools[t].set(expr))

	def copyFrom(self, analysis, src, refs):
		if self is src: return

		if self.mode is input or self.mode is uniform:
			assert False

		assert not src.mode is output

		types = self.refTypes(refs)

		if self.typeField:
			if len(types) == 1:
				analysis.initType(tuple(types)[0], self.typeField)
			else:
				assert src.typeField
				analysis.emitAssign(src.typeField, self.typeField)

		for t in types:
			if intrinsics.isIntrinsicType(t):
				analysis.emit(src.subpools[t].assignTo(self.subpools[t]))


class GLSLTranslator(TypeDispatcher):
	def __init__(self, compiler, poolanalysis, rewriter, ioinfo):
		self.compiler = compiler
		self.poolanalysis = poolanalysis
		self.intrinsicRewrite = rewriter
		self.wrapper = RewriterWrapper(self)

		self.ioinfo = ioinfo

		self.slotInfos = {}

		self.blockStack = []
		self.current = None

		self.inputID   = "inp"
		self.outputID  = "out"
		self.uniformID = "uni"

		self.nameCount = {}

		self.names = {}

		self.subpools = {}

	def subpoolInfo(self, subpool):
		subpool = subpool.forward()

		if subpool not in self.subpools:
			if subpool.intrinsic():
				if not subpool.volatile:
					impl = IntrinsicCopyImpl(subpool)
				elif subpool.unique:
					impl = IntrinsicSingletonImpl(subpool)
				else:
					assert False, "Pooling not yet supported"

			self.subpools[subpool] = impl
		else:
			impl = self.subpools[subpool]

		return impl

	def uniqueNameForSlot(self, slot, mode):
		if slot in self.names:
			return self.names[slot]

		if isinstance(slot, ast.Local) and slot.name:
			prefix = slot.name
		else:
			prefix = "struct"

		if mode is uniform:
			prefix = "%s_%s" % (self.uniformID, prefix)
		elif mode is input:
			prefix = "%s_%s" % (self.inputID, prefix)
		elif mode is output:
			prefix = "%s_%s" % (self.outputID, prefix)

		prefix = self.uniqueName(prefix)
		self.names[slot] = prefix
		if slot in self.ioinfo.same:
			self.names[self.ioinfo.same[slot]] = prefix
		return prefix

	def uniqueName(self, name):
		if name not in self.nameCount:
			self.nameCount[name] = 0
		else:
			count = self.nameCount[name]+1
			self.nameCount[name] = count
			name = "%s_%d" % (name, count)
		return name

	def serializationInfo(self, original):
		slot = self.ioinfo.fieldTrans.get(original, original)

		poolInfo = self.poolanalysis.poolInfoIfExists(slot)
		if poolInfo is None and slot in self.ioinfo.same:
			slot = self.ioinfo.same[slot]
			poolInfo = self.poolanalysis.poolInfoIfExists(slot)

		if not poolInfo:
			return None

		if poolInfo.isSingleton():
			slot = poolInfo.name

		structInfo =  self.slotInfos.get(slot)

		assert structInfo.mode != 'LOCAL', original

		return structInfo

	def pushBlock(self):
		self.blockStack.append(self.current)
		self.current = []

	def popBlock(self):
		block = self.current
		self.current = self.blockStack.pop()
		return glsl.Suite(block)

	def slotInfo(self, slot):
		poolInfo = self.poolanalysis.poolInfo(slot, ())

		assert not poolInfo.isPool()

		if poolInfo.isSingleton():
			slot = poolInfo.name

		if slot not in self.slotInfos:
			if slot in self.ioinfo.outputs:
				mode = output
			elif slot in self.ioinfo.inputs:
				mode = input
			elif slot in self.ioinfo.uniforms:
				mode = uniform
			else:
				mode = local

			info = StructureInfo(self, slot, poolInfo, mode, self.ioinfo.builtin.get(slot))
			self.slotInfos[slot] = info
		else:
			info = self.slotInfos[slot]

		return info

	def typeID(self, t):
		tid = self.poolanalysis.typeIDs[t]
		return glsl.Constant(intrinsics.intrinsicTypeNodes[int], tid)

	def initType(self, t, target):
		self.emitAssign(self.typeID(t), target)

	def emit(self, stmt):
		if stmt is not None:
			self.current.append(stmt)

	def emitAssign(self, expr, target):
		stmt = glsl.Assign(expr, target)
		self.emit(stmt)

	@dispatch(ast.Local, ast.IOName)
	def visitLocal(self, node):
		return self.slotInfo(node)

	@dispatch(ast.Existing)
	def visitExisting(self, node):
		t = node.object.pythonType()
		return glsl.Constant(intrinsics.intrinsicTypeNodes[t], node.object.pyobj)

	@dispatch(ast.DirectCall)
	def visitDirectCall(self, node):
		translated = self.intrinsicRewrite(self.wrapper, node)

		if translated is None:
			raise TemporaryLimitation(self.code, node, "Cannot handle non-intrinsic function calls.")

		return translated

	@dispatch(ast.Load)
	def visitLoad(self, node):
		exprInfo = self(node.expr)
		exprRef = exprInfo.intrinsicRef(node.expr.annotation.references.merged)
		field   = intrinsics.fields[node.name.object.pyobj]
		return glsl.Load(exprRef, field)

	def filteredRefs(self, refs, filter):
			refs = set(refs)
			if filter is not None: refs = refs.intersection(filter)
			return refs

	def transfer(self, expr, targetInfo, filter=None):
		if isinstance(expr, ast.DirectCall):
			assert filter is not None
			expr = self(expr)
			targetInfo.assignIntrinsic(self, filter, expr)
		elif isinstance(expr, ast.Load):
			assert filter is not None
			assert intrinsics.isIntrinsicMemoryOp(expr), expr
			expr = self(expr)
			targetInfo.assignIntrinsic(self, filter, expr)
		elif isinstance(expr, ast.Local):
			refs = self.filteredRefs(expr.annotation.references.merged, filter)
			exprInfo = self(expr)
			targetInfo.copyFrom(self, exprInfo, refs)
		elif isinstance(expr, ast.Existing):
			refs = self.filteredRefs(expr.annotation.references.merged, filter)
			expr = self(expr)
			targetInfo.assignIntrinsic(self, refs, expr)
		else:
			assert False, expr

	@dispatch(ast.Assign)
	def visitAssign(self, node):
		assert len(node.lcls) == 1
		target = node.lcls[0]
		targetInfo = self(target)

		filter = target.annotation.references.merged

		self.transfer(node.expr, targetInfo, filter)

	@dispatch(ast.InputBlock)
	def visitInputBlock(self, node):
		for input in node.inputs:
			src = self(input.src)
			lcl = self(input.lcl)

			refs = input.lcl.annotation.references.merged
			lcl.copyFrom(self, src, refs)

	@dispatch(ast.OutputBlock)
	def visitOutputBlock(self, node):
		for output in node.outputs:
			self.transfer(output.expr, self(output.dst))

	def getCondition(self, condInfo, types):
		parts = [glsl.BinaryOp(condInfo.typeField, '==', self.typeID(te.object.pyobj)) for te in types]

		if len(parts) == 1:
			return parts[0]
		else:
			assert False, parts

	@dispatch(ast.Switch)
	def visitSwitch(self, node):
		condition = node.condition

		self.inlineSuite(condition.preamble)

		condInfo = self(condition.conditional)
		cond = condInfo.intrinsicTypeRef(bool)

		t = self(node.t)
		f = self(node.f)

		self.current.append(glsl.Switch(cond, t, f))

	@dispatch(ast.TypeSwitch)
	def visitTypeSwitch(self, node):
		condInfo = self(node.conditional)

		assert condInfo.typeField

		cases = []

		for case in node.cases:
			condCheck = self.getCondition(condInfo, case.types)

			self.pushBlock()

			if case.expr:
				exprInfo = self(case.expr)
				exprInfo.copyFrom(self, condInfo, case.expr.annotation.references.merged)

			for child in case.body.blocks:
				self(child)

			block = self.popBlock()

			cases.append((condCheck, block))

		last = None

		while cases:
			condCheck, block = cases.pop()

			if last is None:
				last = block
			else:
				last = glsl.Suite([glsl.Switch(condCheck, block, last)])

		self.current.append(last)

	def inlineSuite(self, node):
		for child in node.blocks:
			self(child)

	@dispatch(ast.While)
	def visitWhile(self, node):
		condition = node.condition

		self.inlineSuite(condition.preamble)

		condInfo = self(condition.conditional)
		cond = condInfo.intrinsicTypeRef(bool)

		# TODO preamble -> continue?
		self.pushBlock()
		self.inlineSuite(node.body)
		self.inlineSuite(condition.preamble)
		body = self.popBlock()

		assert len(node.else_.blocks) == 0, "Can't synthesize else blocks?"

		self.current.append(glsl.While(cond, body))

	@dispatch(ast.Discard)
	def visitDiscard(self, node):
		self(node.expr)

	@dispatch(ast.Return)
	def visitReturn(self, node):
		assert len(node.exprs) == 1 and node.exprs[0].object.pyobj is None
		self.current.append(glsl.Return(None))

	@dispatch(ast.Suite)
	def visitSuite(self, node):
		self.pushBlock()
		for child in node.blocks:
			self(child)
		return self.popBlock()

	def process(self, node):
		self.code = node
		suite = self(node.ast)
		return glsl.Code('main', [], glsl.BuiltinType('void'), suite)

def processContext(compiler, trans, context):

	result = trans.process(context.code)
	s = codegen.evaluateCode(compiler, result)

	#print
	#print s
	#print

	context.shaderCode = s

def process(compiler, prgm, exgraph, poolanalysis, shaderprgm, ioinfo):
	rewriter = intrinsics.makeIntrinsicRewriter(compiler.extractor)

	trans = GLSLTranslator(compiler, poolanalysis, rewriter, ioinfo)

	trans.inputID  = "inp"
	trans.outputID = "v2f"
	processContext(compiler, trans, shaderprgm.vscontext)

	trans.inputID  = "v2f"
	trans.outputID = "out"
	processContext(compiler, trans, shaderprgm.fscontext)

	return trans
