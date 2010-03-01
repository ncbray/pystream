from language.python import ast
from analysis.storegraph import storegraph
from ... import intrinsics

import collections

def reindexUnionFind(uf):
	reindexed = {}

	for name in uf:
		group = uf[name]
		if group not in reindexed:
			reindexed[group] = [name]
		else:
			reindexed[group].append(name)

	return reindexed

class Renamer(object):
	def __init__(self):
		self.names = collections.defaultdict(lambda: -1)

	def __call__(self, name):
		self.names[name] += 1
		uid = self.names[name]

		if uid == 0:
			return name
		else:
			return self("%s_%d" % (name, uid))

class SamplerGroup(object):
	def __init__(self, canonical, group, uid):
		self.t = canonical.xtype.obj.pythonType()
		self.canonical = canonical
		self.group = group
		self.name = "samplerGroup%d" % uid
		self.impl = None

		assert len(group) == 1

		self.unique = True

LOCAL   = 'LOCAL'
UNIFORM = 'UNIFORM'
INPUT   = 'INPUT'
OUTPUT  = 'OUTPUT'

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

class SubrefInfo(Mergable):
	def __init__(self):
		Mergable.__init__(self)
		self.name = None
		self.slots = set()
		self.holdsVolatile = False
		self.builtin = False
		self.impl = None

	def merge(self, analysis, other):
		assert isinstance(other, SubrefInfo), other

		self  = self.forward()
		other = other.forward()

		if self is other:
			return self

		other._forward = self

		self.holdsVolatile |= other.holdsVolatile
		self.slots.update(other.slots)

		self.mergeData(other)

		return self

	def postProcess(self, exgraph):
		self.findUnique(exgraph)

	def findUnique(self, exgraph):
		unique = True

		for ref in self.refs:
			unique &= ref.annotation.unique

		if unique:
			exclusive = exgraph.mutuallyExclusive(*self.refs)
			unique &= exclusive

		self.unique = unique

	def intrinsic(self):
		return False

	def setBaseName(self, base, nameCallback):
		if self.name is None:
			if self.holdsVolatile: base = "pool"
			self.name = nameCallback("%s_%s" % (base, self.postfix()))

	def markHoldsVolitile(self, analysis):
		self.holdsVolatile = True
		self.markRefsVolatile(analysis)

class TypeInfo(SubrefInfo):
	@property
	def t(self):
		return int

	def postfix(self):
		return "type"

	def accept(self, visitor, ref):
		return visitor.visitType(ref, self)

class IntrinsicSubrefInfo(SubrefInfo):
	def __init__(self, t):
		SubrefInfo.__init__(self)
		self.t = t
		self.sampler = t in intrinsics.samplerTypes
		self.refs = set()
		self.impl = None

	def postfix(self):
		return self.t.__name__

	def addRef(self, ref):
		if ref not in self.refs:
			self.refs.add(ref)

	def mergeData(self, other):
		assert self.t is other.t
		self.refs.update(other.refs)

	def intrinsic(self):
		return True

	def accept(self, visitor, ref):
		if self.holdsVolatile:
			if self.unique:
				return visitor.visitIntrinsicSingleton(ref, self)
			else:
				return visitor.visitIntrinsicPool(ref, self)
		else:
			return visitor.visitIntrinsicValue(ref, self)


	def markRefsVolatile(self, analysis):
		for ref in self.refs:
			print "mark", ref
			objInfo = analysis.objInfo(ref)
			objInfo.markVolatile(analysis)


class SamplerSubrefInfo(IntrinsicSubrefInfo):
	def accept(self, visitor, ref):
		if self.holdsVolatile:
			assert False, "samplers should not be volatile?"
		else:
			return visitor.visitSampler(ref, self)


class SubpoolLUT(object):
	def __init__(self):
		self.type = None
		self.subpools = {}

	def typeSubpool(self):
		if self.type is None:
			self.type = TypeInfo()
			self.subpools['type'] = self.type
		return self.type

	def getName(self, name):
		sub = self.subpools[name]
		forward = sub.forward()

		if sub is not forward:
			self.subpools[name] = forward
			sub = forward
		return sub

	def intrinsic(self, t):
		assert t in intrinsics.intrinsicTypes, t
		if t not in self.subpools:
			sub = IntrinsicSubrefInfo(t)
			self.subpools[t] = sub
		else:
			sub = self.getName(t)
		return sub

	def sampler(self, t):
		assert t in intrinsics.samplerTypes, t
		if t not in self.subpools:
			sub = SamplerSubrefInfo(t)
			self.subpools[t] = sub
		else:
			sub = self.getName(t)
		return sub


# TODO this is what gets dirty?
class ObjectInfo(object):
	def __init__(self, name):
		self.name = name
		self.subrefs = set()
		self.volatile = False

	def markVolatile(self, analysis):
		if not self.volatile:
			self.volatile = True
			analysis.dirty.add(self)

	def resolve(self, analysis):
			sub = self.subrefs.pop().forward()
			for other in self.subrefs:
				print sub, other
				sub = sub.merge(analysis, other)

			self.subrefs.clear()
			self.subrefs.add(sub)

			sub.markHoldsVolitile(analysis)


class ReferenceInfo(object):
	def __init__(self, output=False):
		self.name = None

		self.slots = set()
		self.refs  = set()

		self.lut = SubpoolLUT()

		self.final = True
		self.output = output

		self.anchor = False

		self.next  = set()
		self.prev  = set()

		self.fieldGroupsRefer = []
		self.containedFieldGroups = []

		self._forward = None

		self.dirty = False


		self.mode = LOCAL

	def subpools(self):
		return self.lut.subpools.itervalues()

	def addSlot(self, slot):
		self.slots.add(slot)

	def addRef(self, ref):
		self.refs.add(ref)

		t = ref.xtype.obj.pythonType()
		if t in intrinsics.samplerTypes:
			sub = self.lut.sampler(t)
			sub.output = self.output
			sub.slots.update(self.slots)
			sub.addRef(ref)
		elif intrinsics.isIntrinsicType(t):
			sub = self.lut.intrinsic(t)
			sub.output = self.output
			sub.slots.update(self.slots)
			sub.addRef(ref)
		else:
			# TODO fields?
			sub = None

		self.final &= ref.annotation.final

		return sub


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

#			if self.final == other.final:
#				print "CONTRACT"
#				print self.slots
#				print other.slots
#				print
#
#				self = self.merge(analysis, other)


	def postProcess(self):
		# Choose a random name
		self.name = tuple(self.slots)[0]

		self.types = set([ref.xtype.obj.pythonType() for ref in self.refs])

		# Make sure it exists
		if self.multipleTypes(): self.lut.typeSubpool()

	def multipleTypes(self):
		return len(self.types) > 1

	def setName(self, name, uniqueCallback):
		self.name = name

		for sub in self.subpools():
			sub.setBaseName(name, uniqueCallback)

	def copyNames(self, other):
		self.name = other.name
		for group, sub in self.lut.subpools.iteritems():
			othersub = other.lut.subpools[group]
			sub.name = othersub.name

	def setSpecialName(self, name):
		self.name = name

		for sub in self.subpools():
			sub.name = name
			sub.builtin = True

	def isSingleton(self):
		return self.unique

	def isStructure(self):
		return not self.unique and self.final

	def isPool(self):
		return not self.unique and not self.final
