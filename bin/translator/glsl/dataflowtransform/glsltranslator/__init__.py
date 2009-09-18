from asttools.transform import *
from analysis.dataflowIR import graph
from analysis.cfgIR import cfg

from language.python import ast
from language.glsl import ast as glsl

from translator.glsl import intrinsics
from translator.glsl.exceptions import TemporaryLimitation

from . slotstruct import SlotStruct
from . poolimplementation import PoolImplementation

from util import ensureValidName

# HACK for debugging
from language.glsl import codegen

class SlotRef(object):
	def __init__(self, ref, struct):
		assert isinstance(ref, glsl.GLSLASTNode) or ref is None, ref
		assert isinstance(struct, SlotStruct), struct
		
		self.ref    = ref
		self.struct = struct

	def ast(self):
		return self.ref

	def value(self, type):
		# HACK
		assert self.struct.inline, self.struct
		return self.ref

class MakeAssign(TypeDispatcher):
	@dispatch(glsl.Local)
	def visitLocal(self, dst, src):
		return glsl.Assign(src, dst)

	@dispatch(glsl.GetSubscript)
	def visitSetSubscript(self, dst, src):
		return glsl.SetSubscript(src, dst.expr, dst.subscript)
	
	@dispatch(glsl.GetAttr)
	def visitGetAttr(self, dst, src):
		return glsl.SetAttr(src, dst.expr, dst.name)

	@dispatch(glsl.Load)
	def visitLoad(self, dst, src):
		return glsl.Store(src, dst.expr, dst.name)

_makeAssign = MakeAssign()

def assign(src, dst):
	return _makeAssign(dst, src)


class RewriterWrapper(TypeDispatcher):
	def __init__(self, translator):
		self.translator = translator

	@dispatch(ast.Local, ast.Existing)
	def visitLocal(self, node):
		slotref = self.translator(node, self.g)
		return slotref.ast()

	@dispatch(list, tuple)
	def visitContainer(self, node):
		return allChildren(self, node)

class GLSLTranslator(TypeDispatcher):
	def __init__(self, code, analysis, poolanalysis, intrinsicRewrite):
		self.code         = code
		self.analysis     = analysis
		self.poolanalysis = poolanalysis

		self.intrinsicRewrite = intrinsicRewrite

		self.wrapper = RewriterWrapper(self)

		self.poolname = {}
		self.uid = 0

		self.indexname = {}

		self.allnames = set()

		self.valuePools = {}

	def getPoolInfo(self, ref, g):
		return self.getPoolInfoForSlot(g.localReads[ref], 0)

	def getPoolInfoForSlot(self, node, index):
		return self.getSlotInfo((node, index)).getPoolInfo()

	def getSlotInfo(self, slot):
			return self.poolanalysis.getSlotInfo(slot)

	# Generate a unique name for each object pool.
	def getPoolImpl(self, info):
		if not info in self.poolname:
			base = 'p%d' % self.uid
			self.uid += 1
			
			impl = PoolImplementation(info, base)
			self.poolname[info] = impl
		else:
			impl = self.poolname[info]
			
		return impl

	def uniqueName(self, suggestion=None):
		if suggestion is None:
			suggestion =''
			name = '_0'
			uid = 0
		else:
			suggestion = ensureValidName(suggestion)
			name = suggestion
			uid  = -1

		while name in self.allnames:
			uid += 1
			name = "%s_%d" % (suggestion, uid)

		self.allnames.add(name)

		return name

	def poolType(self, info, value=False):
		gt = intrinsics.referenceType

		pt = info.singleType()

		if value:
			lut = intrinsics.intrinsicTypeNodes
		else:
			lut = intrinsics.constantTypeNodes

		if pt in lut:
			gt = lut[pt]

		return gt

	def makeLocalForSlot(self, slot, suggestion=None):
			slotinfo = self.getSlotInfo((slot, 0))
			poolinfo = slotinfo.getPoolInfo()

			if poolinfo.canUnbox():
				gt = intrinsics.intrinsicTypeNodes[poolinfo.singleType()]
			else:
				gt = intrinsics.referenceType

			poolimpl = self.getPoolImpl(poolinfo)
			gt = poolimpl.struct.ast

			if suggestion is None and slot.names:
				suggestion = slot.names[0].name

			lcl =  glsl.Local(gt, self.uniqueName(suggestion))

			return lcl

	def uniqueLocalForSlot(self, slot, suggestion=None):
		slot = slot.canonical()
		if not slot in self.indexname:
			lcl = self.makeLocalForSlot(slot, suggestion)
			self.indexname[slot] = lcl
		else:
			lcl = self.indexname[slot]

		return lcl

	def makeConstant(self, value):
		t = intrinsics.constantTypeNodes[type(value)]
		return glsl.Constant(t, value)

	def localRef(self, lcl, g):
		node = g.localReads[lcl]
		return self.localNodeRef(node)

	def localNodeRef(self, lcl):
		assert isinstance(lcl, graph.LocalNode), lcl
		lcl = lcl.canonical()				
		indexName = self.uniqueLocalForSlot(lcl)
		return indexName

	def assignmentTransfer(self, src, g):
		assert isinstance(src, SlotRef), src
		
		if len(g.localModifies) == 0:
			return [] # GLSL has no side effects?
		elif len(g.localModifies) == 1:
			target = g.localModifies[0]
			
			poolInfo = self.getPoolInfoForSlot(target, 0)
			poolImpl = self.getPoolImpl(poolInfo)

			suggestion = target.names[0].name if target.names else None
			index = self.uniqueLocalForSlot(target, suggestion)
			
			dst = SlotRef(index, poolImpl.struct)

			return self.transfer(src, dst)
		else:
			assert False, g

	def transfer(self, src, dst):
		assert isinstance(src, SlotRef), src
		assert isinstance(dst, SlotRef), dst

		# HACK?
		return assign(src.ast(), dst.ast())


	def getSingleSlot(self, tree):
		slots = self.analysis.set.flatten(tree)
		assert len(slots) == 1, slots
		slot = tuple(slots)[0]
		return (slot[0].canonical(), slot[1])

	def slotStruct(self, slot):
		slotInfo = self.getPoolInfoForSlot(*slot)
		slotImpl = self.getPoolImpl(slotInfo)
		return slotImpl.struct

	def slotRef(self, op, slot):
		return SlotRef(op, self.slotStruct(slot))

	def fieldRef(self, node, slot, g):
		expr     = self.localRef(node.expr, g)
		exprInfo = self.getPoolInfo(node.expr, g)
		exprImpl = self.getPoolImpl(exprInfo)
		
		field = slot[0].name.slotName
		
		slotinfo = self.getSlotInfo(slot)
		
		# Force creation.
		self.getPoolImpl(slotinfo.getPoolInfo())
		
		fieldOp  = exprImpl.getField(expr, field, slotinfo)
		
		return self.slotRef(fieldOp, slot)

	def valueRef(self, lcl, g):
		node     = g.localReads[lcl]
		expr     = self.localNodeRef(node)	
		exprInfo = self.getPoolInfo(lcl, g)
		exprImpl = self.getPoolImpl(exprInfo)
		
		# HACK no type
		op = exprImpl.getValue(expr, None)
		
		return self.slotRef(op, (node, 0))

	@dispatch(ast.Load)
	def visitLoad(self, node, g):
		if intrinsics.isIntrinsicMemoryOp(node):
			expr   = self.valueRef(node.expr, g)
			field  = intrinsics.fields[node.name.object.pyobj]
			slot   = self.getSingleSlot(self.analysis.opReads[g])
			src  = self.slotRef(glsl.Load(expr.ast(), field), slot)			
		else:
			slot = self.getSingleSlot(self.analysis.opReads[g])		
			src  = self.fieldRef(node, slot, g)	

		return self.assignmentTransfer(src, g)
		
	@dispatch(ast.Store)
	def visitStore(self, node, g):		
		# Source
		src = self(node.value, g)

		# Destination
		if intrinsics.isIntrinsicMemoryOp(node):		
			expr   = self.valueRef(node.expr, g)
			field  = intrinsics.fields[node.name.object.pyobj]
			slot   = self.getSingleSlot(self.analysis.opModifies[g])
			dst    = self.slotRef(glsl.Load(expr.ast(), field), slot)
		else:
			slot = self.getSingleSlot(self.analysis.opModifies[g])
			dst  = self.fieldRef(node, slot, g)

		return self.transfer(src, dst)


	@dispatch(ast.Allocate)
	def visitAllocate(self, node, g):
		assert len(g.localModifies) == 1

		info = self.getPoolInfoForSlot(g.localModifies[0], 0)
		assert info.isSingleUnique()
		
		src = self.slotRef(self.makeConstant(0), (g.localModifies[0], 0))
		return 	self.assignmentTransfer(src, g)

	@dispatch(ast.Local)
	def visitLocal(self, node, g):
		slot = (g.localReads[node], 0)
		
		lcl = self.localRef(node, g)
				
		return SlotRef(lcl, self.slotStruct(slot))

	@dispatch(ast.Existing)
	def visitExisting(self, node, g):
		value    = self.makeConstant(node.object.pyobj)
		poolinfo = self.getPoolInfo(node, g)
		poolimpl = self.getPoolImpl(poolinfo)
		ref      = SlotRef(value, poolimpl.struct)
		return ref

	@dispatch(list, tuple)
	def visitContainer(self, node, *args):
		return allChildrenArgs(self, node, *args)

	@dispatch(ast.DirectCall)
	def visitDirectCall(self, node, g):
		# HACK intrinsic rewrite may call back, w/o reference to g.
		# Store on self to reconstruct when needed.
		self.wrapper.g = g
		translated = self.intrinsicRewrite(self.wrapper, node)
		del self.wrapper.g

		if translated is None:
			raise TemporaryLimitation(self.code, node, "Cannot handle non-intrinsic function calls.")

		assert len(g.localModifies) == 1
			
		# HACK use assignment target slot.
		target = g.localModifies[0]
		poolInfo = self.getPoolInfoForSlot(target, 0)
		poolImpl = self.getPoolImpl(poolInfo)
		
		targetInfo = self.getSlotInfo((target, 0))
		assert targetInfo.canUnbox()

		src = SlotRef(translated, poolImpl.struct)

		return self.assignmentTransfer(src, g)

	@dispatch(graph.GenericOp)
	def visitGenericOp(self, node):
		stmt = self(node.op, node)
		print stmt
		return stmt

	@dispatch(graph.Exit)
	def visitExit(self, node):
		return glsl.Return(None)

	@dispatch(cfg.CFGBlock)
	def visitCFGBlock(self, node):
		return glsl.Suite([self(op) for op in node.ops])

	@dispatch(cfg.CFGSuite)
	def visitCFGSuite(self, node):
		return glsl.Suite([self(child) for child in node.nodes])

	def process(self, node):
		suite = self(node)
		return glsl.Code('main', [], glsl.BuiltinType('void'), suite)


def process(compiler, code, cfg, dioa, poolanalysis):
	rewriter = intrinsics.makeIntrinsicRewriter(compiler.extractor)

	gt = GLSLTranslator(code, dioa, poolanalysis, rewriter)
	result = gt.process(cfg)

	# HACK for debugging
	print codegen.GLSLCodeGen()(result)

	return result
