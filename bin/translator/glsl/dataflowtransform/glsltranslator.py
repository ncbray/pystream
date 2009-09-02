from asttools.transform import *
from analysis.dataflowIR import graph
from analysis.cfgIR import cfg

from language.python import ast
from language.glsl import ast as glsl

from .. import intrinsics
from .. exceptions import *

import re

invalidNameChar = re.compile('[^\w\d_]')


class ObjectGroup(object):
	def __init__(self):
		self.userObjects      = set()
		self.intrinsicObjects = set()

		self.userTypes        = set()
		self.intrinsicTypes   = set()
		self.constantTypes    = set()

		self.unboxType        = None

class SlotGroup(object):
	def __init__(self):
		self.objectGroup = None
		self.index       = None
		self.unboxType   = None
		self.poolinfo    = None

class GLSLTranslator(TypeDispatcher):
	def __init__(self, code, analysis, poolanalysis, intrinsicRewrite):
		self.code         = code
		self.analysis     = analysis
		self.poolanalysis = poolanalysis

		self.intrinsicRewrite = intrinsicRewrite

		self.poolname = {}
		self.uid = 0

		self.indexname = {}

		self.allnames = set()

		self.bogus      = glsl.BuiltinType('bogus')
		self.reference  = glsl.BuiltinType('ref')

		self.fieldPools = {}
		self.valuePools = {}

	def getPoolInfo(self, ref, g):
		return self.getPoolInfoForSlot(g.localReads[ref], 0)

	def getPoolInfoForSlot(self, node, index):
		return self.poolanalysis.getSlotInfo((node, index)).getPoolInfo()

	def getPoolName(self, info):
		if not info in self.poolname:
			name = 'p%d' % self.uid
			self.uid += 1
			self.poolname[info] = name
		else:
			name = self.poolname[info]
		return name

	def getFieldName(self, info, fieldtype, name):
		key = (info, fieldtype, name)

		if not key in self.fieldPools:
			pname = self.getPoolName(info)
			lcl = glsl.Local(self.reference, self.uniqueName("%s_%s_%s" % (pname, fieldtype, name)))
			self.fieldPools[key] = lcl
		else:
			lcl = self.fieldPools[key]

		return lcl

	def getValueName(self, info):
		key = info

		if not key in self.valuePools:
			isindexed = not info.isSingleUnique()
			unboxed   = info.canUnbox()

			pname = self.getPoolName(info)
			gt = self.poolType(info, value=True)

			lcl = glsl.Local(gt, self.uniqueName("%s_value" % (pname,)))
			self.valuePools[key] = lcl
		else:
			lcl = self.valuePools[key]

		return lcl

	def getRegion(self, info):
		key = info

		if not key in self.valuePools:
			isindexed = not info.isSingleUnique()
			unboxed   = info.canUnbox()
			pname     = self.getPoolName(info)

			if unboxed:
				t = intrinsics.constantTypeNode[info.singleType()]
			else:
				t = self.reference

			if isindexed:
				t = glsl.ArrayType(t, -1)


			lcl = glsl.Local(t, self.uniqueName("%s_value" % (pname,)))
			self.valuePools[key] = lcl
		else:
			lcl = self.valuePools[key]

		return lcl


	def getReference(self, ref, g):
		if isinstance(ref, ast.Local):
			slot = g.localReads[ref].canonical()
			return self.uniqueLocalForSlot(slot, ref.name)
		elif isinstance(ref, ast.Existing):
			# HACK may not point to constant?
			return self.makeConstant(ref.object.pyobj)
		else:
			assert False, ref

	def uniqueName(self, suggestion=None):
		if suggestion is None:
			suggestion =''
			name = '_0'
			uid = 0
		else:
			suggestion = re.sub(invalidNameChar, '_', suggestion)
			name = suggestion
			uid  = -1

		while name in self.allnames:
			uid += 1
			name = "%s_%d" % (suggestion, uid)

		self.allnames.add(name)

		return name

	def poolType(self, info, value=False):
		gt = self.reference

		pt = info.singleType()

		if value:
			lut = intrinsics.intrinsicTypeNodes
		else:
			lut = intrinsics.constantTypeNodes

		if pt in lut:
			gt = lut[pt]

		return gt

	def uniqueLocalForSlot(self, slot, suggestion=None):
		slot = slot.canonical()
		if not slot in self.indexname:
			info = self.getPoolInfoForSlot(slot, 0)
			gt = self.poolType(info)
			lcl =  glsl.Local(gt, self.uniqueName(suggestion))
			self.indexname[slot] = lcl
		else:
			lcl = self.indexname[slot]

		return lcl

	def makeConstant(self, value):
		return glsl.Constant(intrinsics.constantTypeNodes[type(value)], value)

	def getValue(self, lcl, g):
		info = self.getPoolInfo(lcl, g)

		isindexed = not info.isSingleUnique()
		unboxed   = info.canUnbox()


		slot = g.localReads[lcl]

		if unboxed:
			return self.uniqueLocalForSlot(slot, lcl.name)
		else:
			regionname = self.getRegion(info)

			if isindexed:
				getter = glsl.GetSubscript(regionname, self.getReference(lcl, g))
			else:
				getter = regionname

			return getter

	def wrapAssign(self, op, g):
		if len(g.localModifies) == 0:
			stmt = glsl.Discard(op)
		elif len(g.localModifies) == 1:
			target = g.localModifies[0]
			suggestion = target.names[0].name if target.names else None

			stmt = glsl.Assign(op, self.uniqueLocalForSlot(target, suggestion))
		else:
			assert False, g

		return stmt


	def wrapAllocated(self, op, g):
		if len(g.localModifies) == 0:
			stmt = glsl.Discard(op)
		elif len(g.localModifies) == 1:
			target = g.localModifies[0]
			suggestion = target.names[0].name if target.names else None

			stmt = glsl.Assign(op, self.uniqueLocalForSlot(target, suggestion))
		else:
			assert False, g

		return stmt



	@dispatch(ast.Load)
	def visitLoad(self, node, g):
		# Load could be
		# 	Intrinsic load
		# 	Value copy
		# 	Reference copy
		# Load could be
		#	indexed
		#	unindexed

		assert len(g.localModifies) == 1
		target = g.localModifies[0]

		if intrinsics.isIntrinsicMemoryOp(node):
			getter = self.getValue(node.expr, g)
			field = intrinsics.fields[node.name.object.pyobj]
			op = glsl.Load(getter, field)
		else:

			poolinfo = self.getPoolInfo(node.expr, g)
			regionname = self.getFieldName(poolinfo, node.fieldtype, node.name.object.pyobj)

			isindexed = not poolinfo.isSingleUnique()
			unboxed   = poolinfo.canUnbox()

			if unboxed:
				if isindexed:
					op = glsl.GetSubscript(regionname, self.getReference(node.expr, g))
				else:
					op = regionName
			else:
				if isindexed:
					op = glsl.GetSubscript(regionname, self.getReference(node.expr, g))
				else:
					# Reference copy for a constant reference!
					return []

		return self.wrapAssign(op, g)

	@dispatch(ast.Store)
	def visitStore(self, node, g):
		poolinfo = self.getPoolInfo(node.expr, g)

		value = self.getReference(node.value, g)

		if intrinsics.isIntrinsicMemoryOp(node):
			regionname = self.getValueName(poolinfo)

			field = intrinsics.fields[node.name.object.pyobj]

			if poolinfo.isSingleUnique():
				fullname = regionname
			else:
				fullname = glsl.GetSubscript(regionname, self.getReference(node.expr, g))

			return glsl.Store(value, fullname, field)
		else:
			regionname = self.getFieldName(poolinfo, node.fieldtype, node.name.object.pyobj)

			if poolinfo.isSingleUnique():
				return glsl.Assign(value, regionname)
			else:
				return glsl.SetSubscript(value, regionname, self.getReference(node.expr, g))


	@dispatch(ast.Allocate)
	def visitAllocate(self, node, g):
		assert len(g.localModifies) == 1
		info = self.getPoolInfoForSlot(g.localModifies[0], 0)
		assert info.isSingleUnique()
		return 	self.wrapAssign(self.makeConstant(0), g)



	@dispatch(ast.Local)
	def visitLocal(self, node):
		# Note this is always in the context of a direct call, therefore it must reference a value?
		return self.getValue(node, self.g)

	@dispatch(ast.Existing)
	def visitExisting(self, node):
		return self.makeConstant(node.object.pyobj)

	@dispatch(list, tuple)
	def visitContainer(self, node):
		return allChildren(self, node)

	@dispatch(ast.DirectCall)
	def visitDirectCall(self, node, g):
		# HACK
		self.g = g
		translated = self.intrinsicRewrite(self, node)
		del self.g

		if translated is None:
			raise TemporaryLimitation(self.code, node, "Cannot handle non-intrinsic function calls.")

		return self.wrapAllocated(translated, g)

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

from language.glsl import codegen

def process(compiler, code, cfg, dioa, poolanalysis):
	rewriter = intrinsics.makeIntrinsicRewriter(compiler.extractor)

	gt = GLSLTranslator(code, dioa, poolanalysis, rewriter)
	result = gt.process(cfg)


	print codegen.GLSLCodeGen()(result)

	return result