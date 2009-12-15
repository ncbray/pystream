from util.typedispatch import *
import itertools
from .. import intrinsics

from util.graphalgorithim.color import colorGraph

import analysis.dataflowIR.traverse

from analysis.dataflowIR import graph
from language.python import ast

leafTypes = (float, int, bool)


def objectType(obj):
	return obj.xtype.obj.pythonType()


class Mergable(object):
	def __init__(self):
		self._forward = None

	def forward(self):
		if self._forward:
			self._forward = self._forward.forward()
			assert self._forward._forward is None
			return self._forward
		else:
			return self

	def isPoolInfo(self):
		return False

	def isSlotInfo(self):
		return False

class PoolInfo(Mergable):
	def __init__(self):
		Mergable.__init__(self)

		self.objects    = set()
		self.intrinsics = set()
		self.constants  = set()

		self.types      = set()

		self.nonfinal    = False
		self.preexisting = False
		self.allocated   = False

		self.typeTaken   = False

		self.contains    = set()

		# Derived
		self.coloring       = None
		self.uniqueCount    = 0
		self.nonuniqueCount = 0



	def canUnbox(self):
		return self.hasSingleType() and self.constant()

	def constant(self):
		return not self.objects and not self.nonfinal

	def isSingleUnique(self):
		return self.uniqueCount == 1 and self.nonuniqueCount == 0

	def hasSingleType(self):
		return len(self.types) == 1

	def singleType(self):
		if self.hasSingleType():
			return tuple(self.types)[0]
		else:
			return None

	def merge(self, other):
		if self is other:
			return self

		if len(self.objects) < len(other.objects):
			return other.merge(self)

		assert self._forward is None
		assert other._forward is None
		other._forward = self

		self.objects.update(other.objects)
		del other.objects

		self.intrinsics.update(other.intrinsics)
		del other.intrinsics

		self.constants.update(other.constants)
		del other.constants


		self.types.update(other.types)
		del other.types

		self.nonfinal    |= other.nonfinal
		self.preexisting |= other.preexisting
		self.allocated   |= other.allocated
		self.typeTaken   |= other.typeTaken

		self.contains.update(other.contains)
		del other.contains

		return self

	def accumulateType(self, obj, pre):
		self.types.add(objectType(obj))

		if pre:
			self.preexisting = True
		else:
			self.allocated   = True


	def allObjects(self):
		s = set(self.objects)
		s.update(self.intrinsics)
		s.update(self.constants)
		return s

	def dump(self):
			print "Nonfinal", self.nonfinal
			print "Unbox", self.canUnbox()
			print "Pre/Alloc", self.preexisting, "/", self.allocated
			print "U/N", self.uniqueCount, "/", self.nonuniqueCount
			print "Types", sorted(self.types)
			print "Type Taken", self.typeTaken
			print "Contains", sorted(self.contains)
			print sorted(self.objects)
			print sorted(self.intrinsics)
			print sorted(self.constants)
			print

	def isPoolInfo(self):
		return True

class SlotInfo(Mergable):
	def __init__(self):
		Mergable.__init__(self)
		self.slots    = set()
		self.poolinfo = PoolInfo()

	def getPoolInfo(self):
		info = self.poolinfo.forward()
		self.poolinfo = info
		return info

	def canUnbox(self):
		return self.getPoolInfo().canUnbox()

	def merge(self, other):
		if self is other:
			return self

		if len(self.slots) < len(other.slots):
			return other.merge(self)

		assert self._forward is None
		assert other._forward is None

		other._forward = self

		self.slots.update(other.slots)
		self.poolinfo = self.getPoolInfo().merge(other.getPoolInfo())

		return self

	def isSlotInfo(self):
		return True


class PoolAnalysis(TypeDispatcher):
	def __init__(self, compiler, dataflow, analysis):
		self.compiler = compiler
		self.analysis = analysis
		self.dataflow = dataflow

		self.info = {}
		self.slot = {}

		self.nonfinal = set()

	def _initSlotInfo(self, slot, slotinfo):
		assert slot.annotation, slot
		values = slot.annotation.values.flat

		const, intrinsic, user = self.partitionObjects(values)

		poolinfo = slotinfo.getPoolInfo()

		for c in const:
			poolinfo.constants.add(c)
			poolinfo.accumulateType(c, c.annotation.preexisting)

		for subgroup in (intrinsic, user):
			for obj in subgroup:
				objinfo  = self.getPoolInfo(obj)
				poolinfo = poolinfo.merge(objinfo)

	def getSlotInfo(self, slot):
		assert not isinstance(slot, tuple), slot
		slot = slot.canonical()

		if slot not in self.slot:
			info = SlotInfo()
			info.slots.add(slot)
			self._initSlotInfo(slot, info)
		else:
			info = self.slot[slot]
		
		info = info.forward()
		self.slot[slot] = info
		return info

	def slotList(self):
		infos = set()
		for info in self.slot.itervalues():
			infos.add(info.forward())
		return list(infos)

	def handleSlots(self):
		# Initialize all slots
#		for slot in self.analysis._values.iterkeys():
#			if not slot[0].isPredicate() and not slot[0].isExisting() and not slot[0].isNull():
#				self.getSlotInfo(slot)

		analysis.dataflowIR.traverse.dfs(self.dataflow, self)

	def makeCanonical(self, slots):
		for slot in slots:
			assert not isinstance(slot, tuple), slot
			
		return [slot.canonical() for slot in slots]

	def unionSlots(self, *slots):
		canonical = self.makeCanonical(slots)

		info = SlotInfo()
		for slot in canonical:
			if not slot.isPredicate():
				info = info.merge(self.getSlotInfo(slot))

	def logContains(self, expr, slots):
		slots = self.makeCanonical(slots)
		exprPool = self.getSlotInfo(expr).getPoolInfo()
		exprPool.contains.update(slots)

	def linkHeap(self, g):
		# union modifies with their psedo-reads

		for name, mnode in g.heapModifies.iteritems():

			if name in g.heapPsedoReads:
				rnode = g.heapPsedoReads[name]
				if not rnode.isNull():
						self.unionSlots(rnode, mnode)

	def markNonfinal(self, obj):
		self.nonfinal.add(obj)
		self.getPoolInfo(obj).nonfinal = True

	def findNonfinal(self, g):
		alloc = g.annotation.allocate.flat
		mod   = g.annotation.modify.flat

		# Find
		for slot in mod:
			obj = slot.name.object
			nonfinal = obj not in alloc
			if nonfinal:
				self.markNonfinal(obj)

	@dispatch(ast.DirectCall, ast.Allocate)
	def visitOpJunk(self, node, g):
		pass

	@dispatch(ast.Load)
	def visitLoad(self, node, g):
		if not intrinsics.isIntrinsicMemoryOp(node):
			reads = g.annotation.read.flat

			target = g.localModifies[0]
			self.unionSlots(target, *reads)

			expr = g.localReads[node.expr]
			self.logContains(expr, reads)


	@dispatch(ast.Store)
	def visitStore(self, node, g):
		if not intrinsics.isIntrinsicMemoryOp(node):
			modifies = g.annotation.modify.flat

			read = g.localReads[node.value]
			if read.isExisting():
				self.unionSlots(*modifies)
			else:
				value = read
				self.unionSlots(value, *modifies)

			expr = g.localReads[node.expr]
			self.logContains(expr, modifies)


	@dispatch(ast.TypeSwitch)
	def visitTypeSwitch(self, node, g):
		read = g.localReads[node.conditional]
		modifies = g.localModifies
		self.unionSlots(read, *modifies)

		info = self.getSlotInfo(read)
		info.poolinfo.typeTaken = True

	@dispatch(graph.Entry, graph.Exit,
	graph.LocalNode, graph.FieldNode, graph.PredicateNode,
	graph.NullNode, graph.ExistingNode,
	graph.Split,)
	def visitJunk(self, node):
		pass

	@dispatch(graph.GenericOp)
	def visitOp(self, node):
		# TODO union modified fields?
		# What about obviously unique, fields?
		self(node.op, node)
		self.linkHeap(node)
		self.findNonfinal(node)

	@dispatch(graph.Gate)
	def visitGate(self, node):
		self.unionSlots(node.read, node.modify)

	@dispatch(graph.Merge)
	def visitMerge(self, node):
		self.unionSlots(node.modify, *node.reads)


	def getPoolInfo(self, obj):
		t = objectType(obj)

		assert t not in intrinsics.constantTypes, t

		if obj not in self.info:
			info = PoolInfo()

			if t in intrinsics.intrinsicTypes:
				info.intrinsics.add(obj)
			else:
				info.objects.add(obj)

			preexisting = obj.annotation.preexisting
			info.accumulateType(obj, preexisting)
		else:
			info = self.info[obj]
			
		info = info.forward()
		self.info[obj] = info
		return info

	def partitionObjects(self, group):
		const     = []
		intrinsic = []
		user      = []

		for obj in group:
			t = objectType(obj)
			if t in intrinsics.constantTypes:
				const.append(obj)
			elif t in intrinsics.intrinsicTypes:
				intrinsic.append(obj)
			else:
				user.append(obj)

		return const, intrinsic, user

	def unionObjectGroup(self, group):
		const, intrinsic, user = self.partitionObjects(group)

		info = None

		for subgroup in (intrinsic, user):
			for obj in subgroup:
				objinfo = self.getPoolInfo(obj)

				if info is None:
					info = objinfo
					info.constants.update(const)
				else:
					info = info.merge(objinfo)

	def infoList(self):
		infos = set()
		for slotinfo in self.slot.itervalues():
			infos.add(slotinfo.forward().getPoolInfo())

		return list(infos)


	def objectsInterfere(self, a, b):
		maskA = a.annotation.mask
		maskB = b.annotation.mask
		intersect = self.analysis.bool.and_(maskA, maskB)
		return intersect is not self.analysis.bool.false

	def findInterference(self, group):
		# Initialize
		interference = {}
		for obj in group:
			interference[obj] = set()

		# Find interference graph
		if len(group) > 1:
			# n^2... ugly?
			for a, b in itertools.combinations(group, 2):
				if self.objectsInterfere(a, b):
					interference[a].add(b)
					interference[b].add(a)
		return interference

	def colorGroup(self, group):
		interference = self.findInterference(group)
		coloring, grouping, _numColors = colorGraph(interference)
		return coloring, grouping

	def postProcess(self):
		# Annotate final objects
		for obj in self.info.iterkeys():
			if obj not in self.nonfinal:
				obj.annotation = obj.annotation.rewrite(final = True)
		
		# Process pool information
		for pool in self.infoList():
			pool.uniqueCount    = 0
			pool.nonuniqueCount = 0

			objs = pool.allObjects()

			assert objs, objs

			pool.coloring, grouping = self.colorGroup(objs)

			assert grouping, objs
			for subgroup in grouping:
				assert subgroup, objs

				unique    = False
				nonunique = False

				for obj in subgroup:
					if obj.annotation.unique:
						unique = True
					else:
						nonunique = True

				assert unique or nonunique, subgroup

				if unique:    pool.uniqueCount += 1
				if nonunique: pool.nonuniqueCount += 1

	def process(self):
		self.handleSlots()
		self.postProcess()

		if False:
			print
			print "=== Slot Groups ==="
			for info in self.slotList():
				for slot in sorted(info.slots):
					print slot

				poolinfo = info.getPoolInfo()
				poolinfo.dump()
			print


def process(compiler, dataflow, analysis):
	pa = PoolAnalysis(compiler, dataflow, analysis)
	pa.process()
	return pa
