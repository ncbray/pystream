from util.typedispatch import *
import PADS.UnionFind
import collections
import itertools
from .. import intrinsics

from util.graphalgorithim.color import colorGraph

import analysis.dataflowIR.traverse

from analysis.dataflowIR import graph
from language.python import ast

leafTypes = (float, int, bool)

class Mergable(object):
	def __init__(self):
		self._forward = None

	def forward(self):
		if self._forward:
			self._forward = self._forward.forward()
			return self._forward
		else:
			return self

class PoolInfo(Mergable):
	def __init__(self):
		Mergable.__init__(self)

		self.objects    = set()
		self.intrinsics = set()
		self.constants  = set()

		self.nonfinal   = False

		# Derived
		self.types          = None
		self.coloring       = None
		self.uniqueCount    = 0
		self.nonuniqueCount = 0
		self.preexisting    = False
		self.allocated      = False



	def canUnbox(self):
		return len(self.types) == 1 and all([t in intrinsics.constantTypes for t in self.types])

	def isSingleUnique(self):
		return self.uniqueCount == 1 and self.nonuniqueCount == 0

	def hasSingleType(self):
		return len(self.types) == 1

	def singleType(self):
		if len(self.types) == 1:
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
		self.intrinsics.update(other.intrinsics)
		self.constants.update(other.constants)

		self.nonfinal |= other.nonfinal

		return self

class SlotInfo(Mergable):
	def __init__(self):
		Mergable.__init__(self)
		self.slots    = set()
		self.poolinfo = PoolInfo()

	def getPoolInfo(self):
		info = self.poolinfo.forward()
		self.poolinfo = info
		return info

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

class PoolAnalysis(TypeDispatcher):
	def __init__(self, compiler, dataflow, analysis):
		self.compiler = compiler
		self.analysis = analysis
		self.dataflow = dataflow

		self.info = {}
		self.slot = {}

		self.nonfinal = set()

	def _initSlotInfo(self, slot, slotinfo):
		values = self.flatten(self.analysis.getValue(slot[0], slot[1]))

		const, intrinsic, user = self.partitionObjects(values)

		poolinfo = slotinfo.getPoolInfo()
		poolinfo.constants.update(const)

		for subgroup in (intrinsic, user):
			for obj in subgroup:
				objinfo  = self.getPoolInfo(obj)
				poolinfo = poolinfo.merge(objinfo)

	def getSlotInfo(self, slot):
		if slot not in self.info:
			info = SlotInfo()
			info.slots.add(slot)
			self._initSlotInfo(slot, info)
			self.slot[slot] = info
		else:
			info = self.slot[slot].forward()
			self.info[slot] = info

		return info

	def slotList(self):
		infos = set()
		for info in self.slot.itervalues():
			infos.add(info.forward())
		return list(infos)

	def flatten(self, tree):
		return self.analysis.set.flatten(tree)

	def handleSlots(self):
		# Initialize all slots
		for slot in self.analysis._values.iterkeys():
			if not slot[0].isPredicate() and not slot[0].isExisting() and not slot[0].isNull():
				self.getSlotInfo(slot)
		print

		self.slots = PADS.UnionFind.UnionFind()
		analysis.dataflowIR.traverse.dfs(self.dataflow, self)

		inv = collections.defaultdict(set)
		for slot in self.slots:
			inv[self.slots[slot]].add(slot)

	def unionSlots(self, *slots):
		canonical = [(slot.canonical(), index) for slot, index in slots]
		self.slots.union(*canonical)


		info = SlotInfo()
		for slot in canonical:
			if not slot[0].isPredicate():
				info = info.merge(self.getSlotInfo(slot))

	def linkHeap(self, g):
		# union modifies with their psedo-reads

		for name, mnode in g.heapModifies.iteritems():

			if name in g.heapPsedoReads:
				rnode = g.heapPsedoReads[name]
				if not rnode.isNull():
					for i in range(self.analysis.numValues(mnode)):
						self.unionSlots((rnode, i), (mnode, i))

	def markNonfinal(self, obj):
		self.nonfinal.add(obj)
		self.getPoolInfo(obj).nonfinal = True

	def findNonfinal(self, g):
		alloc = self.flatten(self.analysis.opAllocates[g])
		mod   = self.flatten(self.analysis.opModifies[g])

		for slot, index in mod:
			obj = (slot.name.object, index)
			nonfinal = obj not in alloc
			if nonfinal:
				self.markNonfinal(obj)

	@dispatch(ast.DirectCall, ast.Allocate)
	def visitOpJunk(self, node, g):
		pass

	@dispatch(ast.Load)
	def visitLoad(self, node, g):
		if not intrinsics.isIntrinsicMemoryOp(node):
			reads = self.flatten(self.analysis.opReads[g])
			self.unionSlots((g.localModifies[0], 0), *reads)

	@dispatch(ast.Store)
	def visitStore(self, node, g):
		if not intrinsics.isIntrinsicMemoryOp(node):
			read = g.localReads[node.value]

			if read.isExisting(): return

			modifies = self.flatten(self.analysis.opModifies[g])
			self.unionSlots((read, 0), *modifies)

	@dispatch(ast.TypeSwitch)
	def visitTypeSwitch(self, node, g):
		# TODO union locals?

		read = g.localReads[node.conditional]
		modifies = g.localModifies
		self.unionSlots((read, 0), *[(m, 0) for m in modifies])


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
		self.unionSlots((node.read, 0), (node.modify, 0))

	@dispatch(graph.Merge)
	def visitMerge(self, node):
		self.unionSlots((node.modify, 0), *[(r, 0) for r in node.reads])


	def getPoolInfo(self, obj):
		t = self.objectType(obj)

		assert t not in intrinsics.constantTypes, t

		if obj not in self.info:
			info = PoolInfo()

			if t in intrinsics.intrinsicTypes:
				info.intrinsics.add(obj)
			else:
				info.objects.add(obj)

			self.info[obj] = info
		else:
			info = self.info[obj].forward()
			self.info[obj] = info

		return info

	def objectType(self, obj):
		return obj[0].xtype.obj.pythonType()

	def partitionObjects(self, group):
		const     = []
		intrinsic = []
		user      = []

		for obj in group:
			t = self.objectType(obj)
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
		for obj, info in self.info.iteritems():
			infos.add(info.forward())

		return list(infos)

	def buildGroups(self):
		uf = PADS.UnionFind.UnionFind()

		# TODO a none reference will cause problems with the union... special case it?
		# Constants also cause problems?
		for (node, index), values in self.analysis._values.iteritems():
			if node.isPredicate(): continue

			flat = self.flatten(values)
			if flat:
				uf.union(*flat)

		# Invert the union find.
		index = collections.defaultdict(set)
		for ref in uf:
			# Predicates are scattered amoung the values.
			if isinstance(ref, tuple):
				index[uf[ref]].add(ref)

		return index

	def objectsInterfere(self, a, b):
		maskA = self.analysis.objectExistanceMask[a]
		maskB = self.analysis.objectExistanceMask[b]
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
		coloring, grouping, numColors = colorGraph(interference)
		return coloring, grouping


	def processGroup(self, group):
		info = PoolInfo()
		info.objects.update(group)

		info.types = set([obj.xtype.obj.pythonType() for obj, index in group])
		info.polymorphic = len(info.types) > 1
		info.immutable   = all([t in intrinsics.constantTypes for t in info.types])
		assert not info.polymorphic or not info.immutable, group

		if info.immutable:
			return info


		info.coloring, grouping = self.colorGroup(group)
		for subgroup in grouping:
			unique = False
			nonunique = False
			for key in subgroup:
				if self.analysis.isUniqueObject(*key):
					unique = True
				else:
					nonunique = True

				if key in self.analysis.objectPreexisting:
					info.preexisting = True
				else:
					info.allocated   = True

			if unique:    info.uniqueCount += 1
			if nonunique: info.nonuniqueCount += 1

		# These assumptions make synthesis easier.
		#assert nonuniqueCount == 0, group # Temporary until loops are added.
		assert (info.uniqueCount == 0) ^ (info.nonuniqueCount == 0), group
		assert info.preexisting ^ info.allocated, group

		if False:
			print group
			print info.types
			print "U", info.uniqueCount, "N", info.nonuniqueCount, "PRE", info.preexisting, "ALLOC", info.allocated
			print

		return info



	def process(self):
		self.handleSlots()

		index = self.buildGroups()

		lut = {}
		for group in index.itervalues():
			info = self.processGroup(group)
			for obj in info.objects:
				lut[obj] = info

		if True:
			print
			print "=== Nonfinal ==="
			for obj in sorted(self.nonfinal):
				print obj
			print


		if True:
			print
			print "=== Slot Groups ==="
			for info in self.slotList():
				for slot in sorted(info.slots):
					print slot

				poolinfo = info.getPoolInfo()
				print poolinfo.nonfinal
				print sorted(poolinfo.objects)
				print sorted(poolinfo.intrinsics)
				print sorted(poolinfo.constants)
				print
			print

		return lut

def process(compiler, dataflow, analysis):
	pa = PoolAnalysis(compiler, dataflow, analysis)
	return pa.process()

