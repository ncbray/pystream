from util.typedispatch import *
from language.python import ast
from language.glsl import ast as glsl

from translator import intrinsics
from translator.exceptions import TemporaryLimitation

from language.glsl import codegen

from newpoolanalysis import model

import collections


def makeRef(ref, subref):
	bt = intrinsics.intrinsicTypeNodes[subref.t]
	name = subref.name

	if ref.mode is model.OUTPUT:
		return glsl.Output(glsl.OutputDecl(None, False, False, subref.builtin, bt, name))
	elif ref.mode is model.UNIFORM:
		return glsl.Uniform(glsl.UniformDecl(False, bt, name, None))
	elif ref.mode is model.INPUT:
		return glsl.Input(glsl.InputDecl(None, False, subref.builtin, bt, name))
	elif ref.mode is model.LOCAL:
		return glsl.Local(bt, name)
	else:
		assert False, mode

class SubrefImpl(object):
	def __init__(self, refImpl, info):
		self.refImpl = refImpl
		self.info = info

		self.ref = makeRef(refImpl.info, info)

	def getRef(self):
		return self.ref

class TypeImpl(SubrefImpl):
	def copyFrom(self, translator, src, filter):
		types = filterTypes(filter)

		# TODO constant if len(types) == 1

		if len(types) == 1:
			expr = translator.typeID(types.pop())
		else:
			expr = src.ref

		translator.emit(glsl.Assign(expr, self.ref))

def filterTypes(filter):
	types = set()
	for ref in filter:
		types.add(ref.xtype.obj.pythonType())
	return types

def singleType(filter):
	types = filterTypes(filter)
	assert len(types) == 1, types
	return types.pop()

class IntrinsicValueImpl(SubrefImpl):
	def copyFrom(self, translator, src, filter):
		types = filterTypes(filter)

		if self.info.t in types:
			translator.emit(glsl.Assign(src.ref, self.ref))

	def assignIntrinsic(self, translator, expr):
		translator.emit(glsl.Assign(expr, self.ref))

class SamplerImpl(SubrefImpl):
	def __init__(self, refImpl, info, group):
		self.refImpl = refImpl
		self.info = info
		self.group = group

	def getRef(self):
		return self.group.ref

	def copyFrom(self, translator, src, filter):
		assert src.group is self.group

	def assignIntrinsic(self, translator, expr):
		assert False


class RefImpl(object):
	def __init__(self, info):
		self.info = info
		self.subrefs = {}

	def addImpl(self, name, impl):
		self.subrefs[name] = impl

	def copyFrom(self, translator, src, filter):
		for name, subimpl in self.subrefs.iteritems():
			subimpl.copyFrom(translator, src.subrefs[name], filter)

	def intrinsicRef(self, t):
		return self.subrefs[t].getRef()

	def assignIntrinsic(self, trans, t, expr):
		# TODO assign type?
		self.subrefs[t].assignIntrinsic(trans, expr)

	def typeIDRef(self):
		if 'type' not in self.subrefs:
			import pdb
			pdb.set_trace()
		return self.subrefs['type'].getRef()


class BrokenImpl(object):
	def __init__(self):
		bt = intrinsics.intrinsicTypeNodes[int]
		self.ref = glsl.Local(bt, 'broken')

	def copyFrom(self, translator, src, filter):
		translator.emit(glsl.Assign(self.ref, self.ref))

	def intrinsicRef(self, t):
		return self.ref

	def assignIntrinsic(self, trans, t, expr):
		trans.emit(glsl.Assign(expr, self.ref))


class BrokenRef(object):
	def __init__(self):
		self.subrefs = collections.defaultdict(BrokenImpl)

	def copyFrom(self, translator, src, filter):
		for name, subimpl in self.subrefs.iteritems():
			subimpl.copyFrom(translator, src.subrefs[name], filter)

	def intrinsicRef(self, t):
		return self.subrefs[t].getRef()

	def assignIntrinsic(self, trans, t, expr):
		# TODO assign type?
		self.subrefs[t].assignIntrinsic(trans, expr)

	def typeIDRef(self):
		return self.subrefs['type'].getRef()


class RewriterWrapper(TypeDispatcher):
	def __init__(self, translator):
		TypeDispatcher.__init__(self)
		self.translator = translator

	@dispatch(ast.Local)
	def visitLocal(self, node):
		slotref = self.translator(node)
		return slotref.intrinsicRef(singleType(node.annotation.references.merged))

	@dispatch(ast.Existing)
	def visitExisting(self, node):
		return self.translator(node)

	@dispatch(list, tuple)
	def visitContainer(self, node):
		return [self(child) for child in node]


class SamplerGroupImpl(object):
	def __init__(self, info):
		self.info = info
		assert info.unique
		bt = intrinsics.intrinsicTypeNodes[info.t]
		self.ref = glsl.Uniform(glsl.UniformDecl(False, bt, info.name, None))

class GLSLTranslator(TypeDispatcher):
	def __init__(self, compiler, prepassInfo, poolanalysis, rewriter, ioinfo, context):
		self.compiler = compiler
		self.prepassInfo = prepassInfo
		self.poolanalysis = poolanalysis
		self.intrinsicRewrite = rewriter
		self.wrapper = RewriterWrapper(self)

		self.ioinfo = ioinfo

		self.context = context

		self.blockStack = []
		self.current = None


		self.refImpl = {}
		self.subImpl = {}

		self.samplerGroups = {}
		for name, sg in self.prepassInfo.samplerGroups.iteritems():
			self.samplerGroups[name] = SamplerGroupImpl(sg)

		self.buildImpl()

	def samplerGroupImpl(self, sampler):
		return self.samplerGroups[self.prepassInfo.samplers[sampler]]

	def visitType(self, refImpl, subref):
		return TypeImpl(refImpl, subref)

	def visitIntrinsicValue(self, refImpl, subref):
		return IntrinsicValueImpl(refImpl, subref)

	def visitSampler(self, refImpl, subref):
		sampler = tuple(subref.refs)[0]
		return SamplerImpl(refImpl, subref, self.samplerGroupImpl(sampler))

	def buildRef(self, refInfo):
		refImpl = RefImpl(refInfo)

		# Build the subref implementations
		for name, sub in refInfo.lut.subpools.iteritems():
			impl = sub.accept(self, refImpl)
			refImpl.addImpl(name, impl)

		for slot in refInfo.slots:
			self.refImpl[slot] = refImpl

		return refImpl


	def buildImpl(self):
		for name, refInfo in self.prepassInfo.ioRefInfo.iteritems():
			impl = self.buildRef(refInfo)

			alternate = self.ioinfo.fieldTrans.get(name)
			if alternate:
				self.refImpl[alternate] = impl

		for name, refInfo in self.poolanalysis.refInfos.iteritems():
			self.buildRef(refInfo)

	def pushBlock(self):
		self.blockStack.append(self.current)
		self.current = []

	def popBlock(self):
		block = self.current
		self.current = self.blockStack.pop()
		return glsl.Suite(block)

	def typeID(self, t):
		tid = self.prepassInfo.typeIDs[t]
		return glsl.Constant(intrinsics.intrinsicTypeNodes[int], tid)

	def initType(self, t, target):
		self.emitAssign(self.typeID(t), target)

	def emit(self, stmt):
		if stmt is not None:
			self.current.append(stmt)

	def emitAssign(self, expr, target):
		stmt = glsl.Assign(expr, target)
		self.emit(stmt)

	@dispatch(ast.IOName)
	def visitIOName(self, node):
		if node not in self.refImpl:
			node = self.ioinfo.same[node]

		if node not in self.refImpl:
			import pdb
			pdb.set_trace()
			return BrokenRef()

		return self.refImpl[node]


	@dispatch(ast.Local)
	def visitLocal(self, node):
		return self.refImpl[node]

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
		exprRef = exprInfo.intrinsicRef(singleType(node.expr.annotation.references.merged))
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
			targetInfo.assignIntrinsic(self, singleType(filter), expr)
		elif isinstance(expr, ast.Load):
			assert filter is not None
			assert intrinsics.isIntrinsicMemoryOp(expr), expr
			expr = self(expr)
			targetInfo.assignIntrinsic(self, singleType(filter), expr)
		elif isinstance(expr, ast.Local):
			refs = self.filteredRefs(expr.annotation.references.merged, filter)
			exprInfo = self(expr)
			targetInfo.copyFrom(self, exprInfo, refs)
		elif isinstance(expr, ast.Existing):
			refs = self.filteredRefs(expr.annotation.references.merged, filter)
			expr = self(expr)
			targetInfo.assignIntrinsic(self, singleType(refs), expr)
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
		parts = [glsl.BinaryOp(condInfo.typeIDRef(), '==', self.typeID(te.object.pyobj)) for te in types]

		if len(parts) == 1:
			return parts[0]
		else:
			return glsl.ShortCircutOr(parts)

	@dispatch(ast.Switch)
	def visitSwitch(self, node):
		condition = node.condition

		self.inlineSuite(condition.preamble)

		condInfo = self(condition.conditional)
		cond = condInfo.intrinsicRef(bool)

		t = self(node.t)
		f = self(node.f)

		self.current.append(glsl.Switch(cond, t, f))

	@dispatch(ast.TypeSwitch)
	def visitTypeSwitch(self, node):
		condInfo = self(node.conditional)

		cases = []

		for case in node.cases:
			condCheck = self.getCondition(condInfo, case.types)

			self.pushBlock()

			if case.expr and not case.expr.isDoNotCare():
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
		cond = condInfo.intrinsicRef(bool)

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



def processCode(compiler, prgm, exgraph, ioinfo, prepassInfo, poolInfo, context):
	rewriter = intrinsics.makeIntrinsicRewriter(compiler.extractor)

	trans = GLSLTranslator(compiler, prepassInfo, poolInfo, rewriter, ioinfo, context)

	result = trans.process(context.code)
	s = codegen.evaluateCode(compiler, result)

	print
	print s
	print

	context.shaderCode = s
