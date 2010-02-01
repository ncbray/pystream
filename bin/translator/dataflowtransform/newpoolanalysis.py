from util.typedispatch import *
from language.python import ast

import collections
from PADS.UnionFind import UnionFind


class PoolInfo(object):
	def __init__(self, slot, refs):
		self.slots = set([slot])
		self.refs  = set(refs)

		self.final = True
		for ref in refs:
			self.final &= ref.annotation.final

		self.anchor = False

		self.next  = set()
		self.prev  = set()

		self.fieldGroupsRefer = []
		self.containedFieldGroups = []

		self._forward = None

		self.dirty = False

	def forward(self):
		if self._forward:
			self._forward = self._forward.forward()
			assert self._forward._forward is None
			return self._forward
		else:
			return self

	def transfer(self, analysis, other):
		if other is not self:
			self.next.add(other)
			other.prev.add(self)

		return self

	def merge(self, analysis, other):
		self  = self.forward()
		other = other.forward()

		if self is other:
			return self

		assert not self.anchor and not other.anchor

		other._forward = self

		self.slots.update(other.slots)
		self.refs.update(other.refs)

		self.final &= other.final

		# Note that prev and next stay unforwarded, as we'll need to forward
		# everything when we use it, anyways
		self.prev.update(other.prev)
		self.next.update(other.next)

		if other.dirty:
			analysis.dirty.remove(other)

		if not self.dirty:
			analysis.markDirty(self)

		return self

	def updateLinks(self):
		self.prev = set([other.forward() for other in self.prev])
		self.next = set([other.forward() for other in self.next])

		if self in self.prev:
			self.prev.remove(self)

		if self in self.next:
			self.next.remove(self)


	def contract(self, analysis):
		self = self.forward()
		self.updateLinks()

		if self.anchor: return

		others = self.prev.union(self.next)
		for other in others:
			other = other.forward()
			if other.anchor: continue

			if self.final == other.final:
				print "CONTRACT"
				print self.slots
				print other.slots
				print

				self = self.merge(analysis, other)


	def postProcess(self, analysis):
		if len(self.slots) == 1 and isinstance(tuple(self.slots)[0], ast.Local):
			# If there is only one pointer to this pool, it is safe to assume it is unique.
			unique = True
		else:
			unique = True
			for ref in self.refs:
				unique &= ref.annotation.unique

			if unique:
				exclusive = analysis.exgraph.mutuallyExclusive(*self.refs)
				unique &= exclusive

		self.unique = unique

		self.types = set([ref.xtype.obj.pythonType() for ref in self.refs])

		if len(self.types) > 1:
			analysis.ambiguousTypes(self.types)

	def isSingleton(self):
		return self.unique

	def isStructure(self):
		return not self.unique and self.final

	def isPool(self):
		return not self.unique and not self.final

class FieldGroup(object):
	def __init__(self, name, fields, poolInfo):
		self.name     = name
		self.fields   = fields
		self.poolInfo = poolInfo

		poolInfo.fieldGroupsRefer.append(self)

	def __repr__(self):
		return "FieldGroup(%r)" % (self.name,)

class PoolGraphBuilder(TypeDispatcher):
	def __init__(self, exgraph):
		self.exgraph = exgraph
		self.poolInfos  = {}
		self.fieldInfos = {}
		self.typeIDs    = {}
		self.uid = 0

		self.dirty = set()

		self.compatable = UnionFind()

	def reads(self, args):
		self.compatable.union(*args)

	def modifies(self, args):
		self.compatable.union(*args)


	def ambiguousTypes(self, types):
		for t in types:
			if not t in self.typeIDs:
				self.typeIDs[t] = self.uid
				self.uid += 1

	def linkContainedFieldGroups(self, fgs):
		lut = collections.defaultdict(list)

		for fg in fgs:
			objs = set([field.object for field in fg.fields])
			for obj in objs:
				lut[obj].append(fg)

		for info in self.getUniquePools():
			infoFGs = set()
			for ref in info.refs:
				infoFGs.update(lut[ref])
			info.containedFieldGroups = tuple(infoFGs)

	def fieldGroups(self):
		groups = {}
		for obj, group in self.compatable.parents.iteritems():
			if group not in groups:
				groups[group] = [obj]
			else:
				groups[group].append(obj)

		fgs = []
		for name, group in groups.iteritems():
			fg = FieldGroup(name, group, self.fieldInfo(name))
			fgs.append(fg)

		# TODO compress mutually exclusive field groups?
		self.linkContainedFieldGroups(fgs)

		# Create an index
		for fg in fgs:
			for field in fg.fields:
				self.fieldInfos[field] = fg

		return fgs

	def markDirty(self, info):
		assert not info.dirty
		info.dirty = True
		self.dirty.add(info)

	def localInfo(self, slot):
		info = self.poolInfo(slot, slot.annotation.references.merged)
		info.anchor = slot in self.outputAnchors
		return info

	def fieldInfo(self, slot):
		return self.poolInfo(slot, slot)

	def poolInfo(self, slot, refs):
		if slot not in self.poolInfos:
			info = PoolInfo(slot, refs)
			self.poolInfos[slot] = info
			self.markDirty(info)
		else:
			info = self.poolInfos[slot]
			forward = info.forward()
			if info is not forward:
				self.poolInfos[slot] = forward
				info = forward
		return info

	@dispatch(ast.leafTypes, ast.Code, ast.CodeParameters, ast.Return, ast.Existing, ast.DoNotCare)
	def visitLeafs(self, node):
		pass

	@dispatch(ast.Local)
	def visitLocal(self, node):
		return self.localInfo(node)

	@dispatch(ast.DirectCall, ast.Call, ast.Allocate, ast.Load)
	def visitOp(self, node):
		node.visitChildren(self)

	@dispatch(ast.Assign)
	def visitAssign(self, node):
		self(node.expr)

		if isinstance(node.expr, ast.Local):
			expr = self.localInfo(node.expr)
			target = self.localInfo(node.lcls[0])

			expr.transfer(self, target)

		elif isinstance(node.expr, ast.Load):
			load = node.expr
			expr = self.localInfo(load.expr)
			target = self.localInfo(node.lcls[0])

			self.reads(load.annotation.reads.merged)

			src = None
			for field in load.annotation.reads.merged:
				fieldInfo = self.fieldInfo(field)
				if src is None:
					src = fieldInfo
				else:
					src = src.merge(self, fieldInfo)

			src.transfer(self, target)


	@dispatch(ast.Store)
	def visitStore(self, node):
		self.modifies(node.annotation.modifies.merged)

		node.visitAllChildren(self)

		if isinstance(node.value, ast.Local):

			value = self.localInfo(node.value)

			expr  = self.localInfo(node.expr)


			target = None
			for field in node.annotation.modifies.merged:
				fieldInfo = self.fieldInfo(field)
				if target is None:
					target = fieldInfo
				else:
					target = target.merge(self, fieldInfo)

			value.transfer(self, target)

	@dispatch(ast.TypeSwitch)
	def visitTypeSwitch(self, node):
		cond = self.localInfo(node.conditional)
		for case in node.cases:
			expr = self.localInfo(case.expr)
			cond = cond.transfer(self, expr)
			self(case.body)

	@dispatch(ast.Suite)
	def visitOK(self, node):
		node.visitChildren(self)


	def analyzeCode(self, code, outputAnchors):
		self.outputAnchors = outputAnchors
		code.visitChildrenForced(self)

	def process(self):
		while self.dirty:
			info = self.dirty.pop()
			info.dirty = False
			info.contract(self)

		for info in self.getUniquePools():
			info.postProcess(self)

		self.fieldGroups()

	def getUniquePools(self):
		unique = set()

		for info in self.poolInfos.itervalues():
			unique.add(info.forward())

		return unique

	def dump(self):
		for info in self.getUniquePools():
			print "SLOTS"
			for slot in info.slots:
				print '\t', slot
			print "TYPES"
			for t in info.types:
				print '\t', t
			print "REFS"
			for ref in info.refs:
				print '\t', ref
			print "GROUPS REFER"
			for fg in info.fieldGroupsRefer:
				print '\t', fg
			print "GROUPS CONTAINED"
			for fg in info.containedFieldGroups:
				print '\t', fg

			print "FINAL ", info.final
			print "UNIQUE", info.unique
			print
		print

def process(compiler, prgm, exgraph, *contexts):
	pgb = PoolGraphBuilder(exgraph)

	for context in contexts:
		code = context.code
		print code
		pgb.analyzeCode(code, context.shaderdesc.outputs.collectUsed())

	pgb.process()

	pgb.dump()

	return pgb
