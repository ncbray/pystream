from util.typedispatch import *
from language.python import ast
from language.glsl import ast as glsl
import language.glsl.tools

from translator import intrinsics
from translator.exceptions import TemporaryLimitation

from language.glsl import codegen

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


class StructureInfo(object):
	def __init__(self, slot, poolInfo):
		self.slot     = slot
		self.poolInfo = poolInfo

		prefix = "struct"

		if len(self.poolInfo.types) > 1:
			self.typeField = glsl.Local(intrinsics.intrinsicTypeNodes[int], "%s_%s" % (prefix, 'type'))
		else:
			self.typeField = None

		self.intrinsics = {}

		for t in self.poolInfo.types:
			if intrinsics.isIntrinsicType(t):
				lcl = glsl.Local(intrinsics.intrinsicTypeNodes[t], "%s_%s" % (prefix, t.__name__))
				self.intrinsics[t] = lcl

	def refTypes(self, refs):
		return set([ref.xtype.obj.pythonType() for ref in refs])

	def refType(self, refs):
		types = self.refTypes(refs)
		assert len(types) == 1
		return types.pop()

	def intrinsicRef(self, refs):
		t = self.refType(refs)
		return self.intrinsics[t]

	def assignIntrinsic(self, analysis, refs, expr):
		t = self.refType(refs)

		if self.typeField: analysis.initType(t, self.typeField)
		analysis.emitAssign(expr, self.intrinsics[t])

	def copyFrom(self, analysis, src, refs):
		if self is src: return

		types = self.refTypes(refs)

		if self.typeField:
			if len(types) == 1:
				analysis.initType(tuple(types)[0], self.typeField)
			else:
				assert src.typeField
				analysis.emitAssign(src.typeField, self.typeField)

		for t in types:
			if intrinsics.isIntrinsicType(t):
				analysis.emitAssign(src.intrinsics[t], self.intrinsics[t])



class GLSLTranslator(TypeDispatcher):
	def __init__(self, compiler, poolanalysis, rewriter):
		self.compiler = compiler
		self.poolanalysis = poolanalysis
		self.intrinsicRewrite = rewriter
		self.wrapper = RewriterWrapper(self)

		self.slotInfos = {}

		self.blockStack = []
		self.current = None

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
			info = StructureInfo(slot, poolInfo)
			self.slotInfos[slot] = info
		else:
			info = self.slotInfos[slot]

		return info

	def typeID(self, t):
		tid = self.poolanalysis.typeIDs[t]
		return glsl.Constant(intrinsics.intrinsicTypeNodes[int], tid)

	def initType(self, t, target):
		self.emitAssign(self.typeID(t), target)

	def emitAssign(self, expr, target):
		self.current.append(glsl.Assign(expr, target))

	@dispatch(ast.Local)
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

	@dispatch(ast.Assign)
	def visitAssign(self, node):
		assert len(node.lcls) == 1
		target = node.lcls[0]
		targetInfo = self(target)

		if isinstance(node.expr, ast.DirectCall):
			expr = self(node.expr)
			targetInfo.assignIntrinsic(self, node.lcls[0].annotation.references.merged, expr)

		elif isinstance(node.expr, ast.Load):
			load = node.expr
			assert intrinsics.isIntrinsicMemoryOp(load), load

			expr = self(node.expr)
			targetInfo.assignIntrinsic(self, node.lcls[0].annotation.references.merged, expr)

		elif isinstance(node.expr, ast.Local):
			refs = set(node.expr.annotation.references.merged).intersection(target.annotation.references.merged)
			exprInfo = self(node.expr)
			targetInfo.copyFrom(self, exprInfo, refs)
		elif isinstance(node.expr, ast.Existing):
			expr = self(node.expr)
			targetInfo.assignIntrinsic(self, node.expr.annotation.references.merged, expr)
		else:
			assert False, node.expr

	def getCondition(self, condInfo, types):
		parts = [glsl.BinaryOp(condInfo.typeField, '==', self.typeID(te.object.pyobj)) for te in types]

		if len(parts) == 1:
			return parts[0]
		else:
			assert False, parts

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

		assert len(cases) == 2

		self.current.append(glsl.Switch(cases[0][0], cases[0][1], cases[1][1]))

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
		suite = self(node.ast)
		return glsl.Code('main', [], glsl.BuiltinType('void'), suite)

def processContext(compiler, prgm, exgraph, poolanalysis, rewriter, context):
	trans = GLSLTranslator(compiler, poolanalysis, rewriter)
	result = trans.process(context.code)
	s = codegen.evaluateCode(compiler, result)

	print
	print s
	print

def process(compiler, prgm, exgraph, poolanalysis, *contexts):
	rewriter = intrinsics.makeIntrinsicRewriter(compiler.extractor)

	for context in contexts:
		processContext(compiler, prgm, exgraph, poolanalysis, rewriter, context)
