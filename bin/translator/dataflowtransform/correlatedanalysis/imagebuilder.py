from language.python import ast
from analysis.dataflowIR import graph
from util.monkeypatch import xcollections

leafTypes = (float, int, bool)

def isLeaf(ref):
	if ref.xtype.isExisting():
		# Naturaly unique
		return True
	else:
		# Constants don't need to be unique
		return isConstantType(ref)

def isConstantType(ref):
	o = ref.xtype.obj
	return issubclass(o.pythonType(), leafTypes)

def createIndex(analysis, ref):
	if isLeaf(ref):
		# The object is either a constant or a unique object.
		if analysis.getCount(ref) == 0:
			analysis.incrementCount(ref, unique=True)
		count = 0
	else:
		count = analysis.incrementCount(ref, unique=True)
	return count

class InputMemoryImageBuilder(object):
	def __init__(self, analysis):
		self.analysis = analysis
		self.pathRefs = xcollections.defaultdict(set)
		self.process()

	def extendPath(self, path, slot):
		name = slot.slotName
		newPath = path + (name,)
		return newPath

	def inspectPath(self, path, refs):
		entrySlots = self.analysis.dataflow.entry.modifies

		for ref in refs:
			if ref in self.pathRefs[path]: continue

			self.pathRefs[path].add(ref)
			for nextslot in ref:
				# If it's not defined, it's not used.
				if nextslot in entrySlots:
					self.inspectPath(self.extendPath(path, nextslot), nextslot)

	# Collects all possible objects for each unique path.
	# Relies on a lack of circular references in the memory image.
	# If recursive structures are ever allowed, we'll need to collapse SCCs.
	def findTypes(self):
		# Figure out the possible types for each unique path.
		for name, node in self.analysis.dataflow.entry.modifies.iteritems():
			if isinstance(node, graph.LocalNode):
				self.inspectPath((name.name,), name.annotation.references.merged)



	def buildPath(self, node, index, path, refs, mask):
		assert isinstance(node, graph.SlotNode), node
		assert isinstance(index, int), index

		entrySlots = self.analysis.dataflow.entry.modifies

		cond = self.pathCondition(path)

		for ref in refs:
			key = path, ref

			# Create a new object, if we haven't.
			if key not in self.analysis.pathObjIndex:
				count = createIndex(self.analysis, ref)
				self.analysis.pathObjIndex[key] = count
			else:
				count = self.analysis.pathObjIndex[key]

			if cond is not None:
				refmask = self.analysis.bool.and_(cond.mask[ref], mask)
			else:
				refmask = mask


			# Build the reference
			leaf = self.analysis.set.leaf([(ref, count)])
			leaf = self.analysis.set.ite(refmask, leaf, self.analysis.set.empty)

			# Merge in the reference
			old = self.analysis.getValue(node, index)
			merged = self.analysis.set.union(old, leaf)
			self.analysis.setValue(node, index, merged)

			# Keep track of the conditions underwhich the object exists.
			self.analysis.objectPreexisting.add((ref, count))
			self.analysis.accumulateObjectExists(ref, count, refmask)

			# Recurse
			for nextslot in ref:
				# If it's not defined, it's not used.
				if nextslot in entrySlots:
					nextnode = entrySlots[nextslot]
					self.buildPath(nextnode, count, self.extendPath(path, nextslot), nextslot, refmask)

	def buildImage(self):
		for name, node in self.analysis.dataflow.entry.modifies.iteritems():
			if isinstance(node, graph.LocalNode):
				self.buildPath(node, 0, (name.name,), name.annotation.references.merged, self.analysis.bool.true)

	def process(self):
		self.findTypes()
		self.buildImage()

	def pathCondition(self, path):
		if len(self.pathRefs[path]) > 1:
			return self.analysis.cond.condition(path, sorted(self.pathRefs[path]))
		else:
			return None

class AllocationMemoryImageBuilder(object):
	def __init__(self, analysis):
		self.analysis = analysis
		self.process()

	def process(self):
		for g in self.analysis.order:
			if isinstance(g, graph.GenericOp):
				op = g.op
				if isinstance(op, ast.TypeSwitch): continue

				assert op.annotation.allocates is not None, op
				allocates = op.annotation.allocates.merged
				for obj in allocates:
					self.analysis.allocateFreshIndex[obj] = createIndex(self.analysis, obj)
					#self.analysis.allocateMergeIndex[obj] = createIndex(self.analysis, obj)

def build(analysis):
	InputMemoryImageBuilder(analysis)
	AllocationMemoryImageBuilder(analysis)
