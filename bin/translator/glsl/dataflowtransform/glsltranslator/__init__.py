from asttools.transform import *
from analysis.dataflowIR import graph
from analysis.cfgIR import cfg

from language.python import ast
from language.glsl import ast as glsl
import language.glsl.tools

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
	def __init__(self, code, poolanalysis, intrinsicRewrite):
		self.code         = code
		self.poolanalysis = poolanalysis

		self.intrinsicRewrite = intrinsicRewrite

		self.wrapper = RewriterWrapper(self)

		self.poolname = {}
		self.uid = 0

		self.indexname = {}

		self.allnames = set()

		self.valuePools = {}

	def getPoolInfoForSlot(self, slot):
		return self.getSlotInfo(slot).getPoolInfo()

	def getSlotInfo(self, slot):
		return self.poolanalysis.getSlotInfo(slot)

	# Generate a unique name for each object pool.
	def getPoolImplForInfo(self, info):
		if not info in self.poolname:
			base = 'p%d' % self.uid
			self.uid += 1
			
			impl = PoolImplementation(info, base)
			self.poolname[info] = impl
		else:
			impl = self.poolname[info]
			
		return impl

	def getPoolImpl(self, slot):
		info = self.getPoolInfoForSlot(slot)
		return self.getPoolImplForInfo(info)

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

	def makeLocalForSlot(self, slot, suggestion=None):
			slotinfo = self.getSlotInfo(slot.canonical())
			poolinfo = slotinfo.getPoolInfo()

			poolimpl = self.getPoolImplForInfo(poolinfo)
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
			
			slot     = target.canonical()
			poolImpl = self.getPoolImpl(slot)

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
		return language.glsl.tools.assign(src.ast(), dst.ast())


	def getSingleSlot(self, value):
		# HACK ugly, ignores cases with more than one slot!
		return tuple(value)[0]

	def slotStruct(self, slot):
		return self.getPoolImpl(slot).struct

	def slotRef(self, op, slot):
		return SlotRef(op, self.slotStruct(slot))

	def fieldRef(self, node, slot, g):
		exprSlot = g.localReads[node.expr].canonical()
		
		expr     = self.localRef(node.expr, g)
		exprImpl = self.getPoolImpl(exprSlot)
		
		field    = slot.name.slotName
		slotinfo = self.getSlotInfo(slot)
			
		# Force creation.
		self.getPoolImpl(slot)
		
		fieldOp  = exprImpl.getField(expr, field, slotinfo)
		
		return self.slotRef(fieldOp, slot)

	def valueRef(self, lcl, g):
		node     = g.localReads[lcl]
		slot     = node.canonical()
		expr     = self.localNodeRef(node)	
		exprImpl = self.getPoolImpl(slot)
		
		# HACK no type
		op = exprImpl.getValue(expr, None)
		
		return self.slotRef(op, node.canonical())

	@dispatch(ast.Load)
	def visitLoad(self, node, g):
		slot   = self.getSingleSlot(g.annotation.read.flat)

		if intrinsics.isIntrinsicMemoryOp(node):
			expr   = self.valueRef(node.expr, g)
			field  = intrinsics.fields[node.name.object.pyobj]
			src    = self.slotRef(glsl.Load(expr.ast(), field), slot)			
		else:
			src  = self.fieldRef(node, slot, g)	

		return self.assignmentTransfer(src, g)
		
	@dispatch(ast.Store)
	def visitStore(self, node, g):		
		# Source
		src = self(node.value, g)

		slot   = self.getSingleSlot(g.annotation.modify.flat)

		# Destination
		if intrinsics.isIntrinsicMemoryOp(node):		
			expr   = self.valueRef(node.expr, g)
			field  = intrinsics.fields[node.name.object.pyobj]
			dst    = self.slotRef(glsl.Load(expr.ast(), field), slot)
		else:
			dst  = self.fieldRef(node, slot, g)

		return self.transfer(src, dst)


	@dispatch(ast.Allocate)
	def visitAllocate(self, node, g):
		assert len(g.localModifies) == 1

		slot = g.localModifies[0].canonical()
		info = self.getPoolInfoForSlot(slot)
		
		if False:
			if not info.isSingleUnique():
				info.dump()
				
			assert info.isSingleUnique(), node
		
		impl = self.getPoolImpl(slot)
		return impl.allocate(self, slot, g)

	@dispatch(ast.Local)
	def visitLocal(self, node, g):
		slot = g.localReads[node].canonical()
		lcl  = self.localRef(node, g)				
		return SlotRef(lcl, self.slotStruct(slot))

	@dispatch(ast.Existing)
	def visitExisting(self, node, g):
		value    = self.makeConstant(node.object.pyobj)
		slot     = g.localReads[node].canonical()
		poolimpl = self.getPoolImpl(slot)
		ref      = SlotRef(value, poolimpl.struct)
		return ref

	@dispatch(list, tuple)
	def visitContainer(self, node):
		return allChildren(self, node)

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
		slot = target.canonical()
		poolimpl = self.getPoolImpl(slot)
		
		targetInfo = self.getSlotInfo(slot)
		assert targetInfo.canUnbox()

		src = SlotRef(translated, poolimpl.struct)

		return self.assignmentTransfer(src, g)

	# HACK remains in CFG, null it out.
	@dispatch(ast.TypeSwitch)
	def visitTypeSwitch(self, node, g):
		return []

	@dispatch(graph.GenericOp)
	def visitGenericOp(self, node):
		stmt = self(node.op, node)
		return stmt

	@dispatch(graph.Gate)
	def visitGate(self, node):
		srcSlot = node.read.canonical()
		lcl  = self.localNodeRef(srcSlot)				
		src = SlotRef(lcl, self.slotStruct(srcSlot))	

		dstSlot = node.modify.canonical()
		lcl  = self.localNodeRef(dstSlot)				
		dst = SlotRef(lcl, self.slotStruct(dstSlot))	

		return self.transfer(src, dst)

	@dispatch(graph.Exit)
	def visitExit(self, node):
		return glsl.Return(None)

	@dispatch(cfg.CFGTypeSwitch)
	def visitCFGTypeSwitch(self, node):
		#op = node.switch.op
		
		cases = [self(case) for case in node.cases]

		current = cases.pop()
		
		while cases:
			case = cases.pop()
			condition = glsl.Local(intrinsics.intrinsicTypeNodes[bool], 'bogus')
			current = glsl.Switch(condition, case, current)

		#node.merge
		
		return current

	@dispatch(cfg.CFGBlock)
	def visitCFGBlock(self, node):
		return glsl.Suite([self(op) for op in node.ops])

	@dispatch(cfg.CFGSuite)
	def visitCFGSuite(self, node):
		return glsl.Suite([self(child) for child in node.nodes])

	def process(self, node):
		suite = self(node)
		return glsl.Code('main', [], glsl.BuiltinType('void'), suite)


def process(compiler, code, cfg, poolanalysis):
	rewriter = intrinsics.makeIntrinsicRewriter(compiler.extractor)

	gt = GLSLTranslator(code, poolanalysis, rewriter)
	result = gt.process(cfg)

	# HACK for debugging
	print codegen.GLSLCodeGen()(result)

	return result
