from language.python import ast

class Hyperblock(object):
	__slots__ = 'name'

	def __init__(self, name):
		self.name = name

	def __repr__(self):
		return "hyperblock(%s)" % str(self.name)

class DataflowNode(object):
	__slots__ = 'hyperblock', 'canonicalpredicate'

	def __init__(self, hyperblock, cp):
		assert hyperblock is None or isinstance(hyperblock, Hyperblock), type(hyperblock)
		assert cp is None or isinstance(cp, PredicateNode), type(cp)

		self.hyperblock = hyperblock
		self.canonicalpredicate = cp.canonical() if cp is not None else cp


class SlotNode(DataflowNode):
	__slots__ = ()

	def addUse(self, op):
		raise NotImplementedError, type(self)

	def removeUse(self, op):
		raise NotImplementedError, type(self)

	def addDefn(self, op):
		raise NotImplementedError, type(self)

	def removeDefn(self, op):
		raise NotImplementedError, type(self)

	def canonical(self):
		return self

	def mustBeUnique(self):
		return True

	def isLocal(self):
		return False

	def isField(self):
		return False

	def isPredicate(self):
		return False

	def definingOp(self):
		return None


class FlowSensitiveSlotNode(SlotNode):
	__slots__ = 'defn', 'use'

	def __init__(self, hyperblock, cp):
		SlotNode.__init__(self, hyperblock, cp)
		self.defn  = None
		self.use   = None

	def addDefn(self, op):
		# HACK should we allow redundant setting, or force a merge?
		assert self.defn is None or self.defn is op, (self, op)
		self.defn = op
		return self

	def removeDefn(self, op):
		assert self.defn is op
		self.defn = None

	def addUse(self, op):
		if self.use is None:
			self.use = op
			return self
		elif self.defn.isSplit():
			# This slot is the product of a split, pass the use on
			# to the original.  This prevents us from having more than
			# one level of split.
			return self.defn.read.addUse(op)
		else:
			if not self.use.isSplit():
				# Redirect the current use
				dup = self.duplicate()
				dup.use = self.use
				self.use.replaceUse(self, dup)

				# Replace the current use with a split
				split = Split(self.hyperblock)
				split.read = self
				split.addModify(dup)
				self.use = split

			# Redirect to the output of the split.
			dup = self.duplicate().addUse(op)
			self.use.addModify(dup)

			#self.use.sanityCheck()

			return dup

	def removeUse(self, op):
		assert self.use is op
		self.use = None

	def forward(self):
		if self.use is not None:
			return (self.use,)
		else:
			return ()

	def reverse(self):
		assert self.defn is not None, self
		return (self.defn,)


	def canonical(self):
		if isinstance(self.defn, Split):
			return self.defn.read.canonical()
		else:
			return self

	def isUse(self, op):
		return op is self.use, (op, self.use)

	def isDefn(self, op):
		return op is self.defn, (op, self.defn)

	def isMutable(self):
		return True

	def definingOp(self):
		if isinstance(self.defn, Split):
			return self.defn.read.definingOp()
		else:
			return self.defn


class LocalNode(FlowSensitiveSlotNode):
	__slots__ = 'names'
	def __init__(self, hyperblock, cp, names=()):
		FlowSensitiveSlotNode.__init__(self, hyperblock, cp)
		self.names = [name for name in names]

	def addName(self, name):
		#assert isinstance(name, ast.Local), name
		if name not in self.names:
			self.names.append(name)

	def duplicate(self):
		node = LocalNode(self.hyperblock, self.canonicalpredicate)
		# HACK shares the names, so any updates will be seen by all versions of the node.
		node.names = self.names
		return node

	def __repr__(self):
		return "lcl(%s)" % ", ".join([repr(name) for name in self.names])

	def isLocal(self):
		return True


class PredicateNode(FlowSensitiveSlotNode):
	__slots__ = 'source', 'name'
	def __init__(self, hyperblock, cp, source, name):
		FlowSensitiveSlotNode.__init__(self, hyperblock, cp)
		self.source = source
		self.name = name

	def duplicate(self):
		node = PredicateNode(self.hyperblock, self.canonicalpredicate, self.source, self.name)
		return node

	def __repr__(self):
		return "pred(%s)" % self.name

	def isPredicate(self):
		return True


class ExistingNode(SlotNode):
	__slots__ = 'name', 'ref', 'uses'
	def __init__(self, name, ref):
		SlotNode.__init__(self, None, None)
		self.name = name
		self.ref  = ref
		self.uses = []

	def addName(self, name):
		# May get called when an existing is copied to a local?
		if isinstance(name, ast.Existing):
			obj = name.object
			if self.name is None:
				self.name = obj
			else:
				assert self.name is obj

	def addUse(self, op):
		self.uses.append(op)
		return self

	def removeUse(self, op):
		self.uses.remove(op)

	def duplicate(self):
		return self

	def __repr__(self):
		return "exist(%r)" % self.name

	def forward(self):
		return self.uses

	def reverse(self):
		return ()

	def isUse(self, op):
		return op in self.uses

	def isMutable(self):
		return False


class NullNode(SlotNode):
	__slots__ = 'defn', 'uses'
	def __init__(self):
		SlotNode.__init__(self, None, None)
		self.defn = None
		self.uses = []

	def addName(self, name):
		pass

	def addDefn(self, op):
		assert isinstance(op, Entry), op
		assert self.defn is None
		self.defn = op
		return self

	def addUse(self, op):
		self.uses.append(op)
		return self

	def removeUse(self, op):
		self.uses.remove(op)

	def duplicate(self):
		return self

	def __repr__(self):
		return "null()"

	def forward(self):
		return self.uses

	def reverse(self):
		return ()

	def isUse(self, op):
		return op in self.uses

	def isMutable(self):
		return False


class FieldNode(FlowSensitiveSlotNode):
	__slots__ = 'name'
	def __init__(self, hyperblock, cp, name):
		FlowSensitiveSlotNode.__init__(self, hyperblock, cp)
		self.name = name

	def addName(self, name):
		if self.name is None:
			self.name = name
		else:
			assert self.name is name, (self.name, name)

	def duplicate(self):
		node = FieldNode(self.hyperblock, self.canonicalpredicate, self.name)
		return node

	def __repr__(self):
		return "field(%r)" % self.name

	def mustBeUnique(self):
		return False

	def isField(self):
		return True


class OpNode(DataflowNode):
	__slots__ = ()

	def isMerge(self):
		return False

	def isSplit(self):
		return False

	def isBranch(self):
		return False

	def setPredicate(self, p):
		assert p.hyperblock is self.hyperblock,  (self.hyperblock, p.hyperblock)

		if self.predicate is not None:
			self.predicate.removeUse(self)
		self.predicate = p
		if self.predicate is not None:
			self.predicate = self.predicate.addUse(self)

class Entry(OpNode):
	__slots__ = 'modifies'

	def __init__(self, hyperblock):
		OpNode.__init__(self, hyperblock, None)
		self.modifies = {}

	def addEntry(self, name, slot):
		assert name not in self.modifies
		slot = slot.addDefn(self)
		self.modifies[name] = slot
		#self.sanityCheck()

	def __repr__(self):
		return "entry()"

	def forward(self):
		return self.modifies.itervalues()

	def reverse(self):
		return ()

	def sanityCheck(self):
		for slot in self.modifies.itervalues():
			assert slot.isDefn(self)


class Exit(OpNode):
	__slots__ = 'predicate', 'reads'

	def __init__(self, hyperblock, cp):
		OpNode.__init__(self, hyperblock, cp)
		self.predicate = None
		self.reads     = {}

	def addExit(self, name, slot):
		assert name not in self.reads
		slot = slot.addUse(self)
		self.reads[name] = slot
		#self.sanityCheck()

	def __repr__(self):
		return "exit()"

	def forward(self):
		return ()

	def reverse(self):
		return [self.predicate] + self.reads.values()

	def sanityCheck(self):
		for slot in self.reads.itervalues():
			assert slot.isUse(self)

class Gate(OpNode):
	__slots__ = 'predicate', 'read', 'modify'
	def __init__(self, hyperblock, cp):
		OpNode.__init__(self, hyperblock, cp)
		self.predicate = None
		self.read = None
		self.modify = None

	def isSplit(self):
		return True

	def addRead(self, slot):
		assert self.read is None
		slot = slot.addUse(self)
		self.read = slot
		#self.sanityCheck()

	def addModify(self, slot):
		assert self.modify is None
		slot = slot.addDefn(self)
		self.modify = slot
		#self.sanityCheck()

	def replaceUse(self, original, replacement):
		if self.predicate is original:
			self.predicate = replacement
		else:
			assert self.read is original
			self.read = replacement
		#self.sanityCheck()

	def replaceDefn(self, original, replacement):
		assert self.modify is original
		self.modify = replacement
		#self.sanityCheck()

	def __repr__(self):
		return "gate(%r, %r)" % (self.read, self.predicate)

	def forward(self):
		return (self.modify,)

	def reverse(self):
		assert self.read is not None
		return (self.read, self.predicate)


class Merge(OpNode):
	__slots__ = 'reads', 'modify'

	def __init__(self, hyperblock):
		OpNode.__init__(self, hyperblock, None)
		self.reads  = []
		self.modify = None

	def isMerge(self):
		return True

	def addRead(self, slot):
		assert slot.hyperblock is not self.hyperblock
		slot = slot.addUse(self)
		self.reads.append(slot)
		#self.sanityCheck()

	def addModify(self, slot):
		assert self.modify is None
		assert slot.hyperblock is self.hyperblock
		slot = slot.addDefn(self)
		self.modify = slot
		#self.sanityCheck()

	def replaceUse(self, original, replacement):
		hit = replaceList(self.reads, original, replacement)
		assert hit, original
		#self.sanityCheck()

	def replaceDefn(self, original, replacement):
		assert self.modify is original
		self.modify = replacement
		#self.sanityCheck()

	def __repr__(self):
		return "merge(%r, %d)" % (self.modify, len(self.reads))

	def forward(self):
		assert self.modify is not None
		return (self.modify,)

	def reverse(self):
		return self.reads

	def sanityCheck(self):
		assert self.modify not in self.reads

		for slot in self.reads:
			assert slot.isUse(self)

		assert self.modify.isDefn(self)

class Split(OpNode):
	__slots__ = 'read', 'modifies'
	def __init__(self, hyperblock):
		OpNode.__init__(self, hyperblock, None)
		self.read = None
		self.modifies = []

	def isSplit(self):
		return True

	def addRead(self, slot):
		assert self.read is None
		slot = slot.addUse(self)
		self.read = slot
		#self.sanityCheck()

	def addModify(self, slot):
		slot = slot.addDefn(self)
		self.modifies.append(slot)
		#self.sanityCheck()

	def replaceUse(self, original, replacement):
		assert self.read is original
		self.read = replacement
		#self.sanityCheck()

	def replaceDefn(self, original, replacement):
		hit = replaceList(self.modifies, original, replacement)
		assert hit, original
		#self.sanityCheck()

	def __repr__(self):
		return "split(%r, %d)" % (self.read, len(self.modifies))

	def forward(self):
		return self.modifies

	def reverse(self):
		assert self.read is not None
		return (self.read,)

	def optimize(self):
		if len(self.modifies) == 1:
			new = self.read
			old = self.modifies[0]
			old.use.replaceUse(old, new)
			new.use = old.use

			self.read = None
			self.modifies = []
			return new
		else:
			return self

	def sanityCheck(self):
		assert self.read not in self.modifies

		assert self.read.isUse(self)

		for slot in self.modifies:
			assert slot.isDefn(self)

def replaceList(l, original, replacement):
	if original in l:
		index = l.index(original)
		l[index] = replacement
		return True
	else:
		return False

class GenericOp(OpNode):
	__slots__ = 'predicate', 'op', 'localReads', 'localModifies', 'heapReads', 'heapModifies', 'heapPsedoReads', 'predicates'
	def __init__(self, hyperblock, cp, op):
		OpNode.__init__(self, hyperblock, cp)
		self.predicate      = None
		self.op             = op

		self.localReads     = {}

		self.heapReads      = {}
		self.heapModifies   = {}
		self.heapPsedoReads = {}

		# Outputs
		self.localModifies  = []
		self.predicates     = []

	def isBranch(self):
		return isinstance(self.op, (ast.TypeSwitch, ast.Switch))

	def replaceUse(self, original, replacement):
		if isinstance(original, PredicateNode):
			assert original is self.predicate
			self.predicate = replacement
		elif isinstance(original, (LocalNode, ExistingNode)):
			assert isinstance(replacement, (LocalNode, ExistingNode)), replacement
			for name in original.names:
				if name in self.localReads and original is self.localReads[name]:
					self.localReads[name] = replacement
					break
			else:
				assert False, (original, self.localReads)
		else:

			if original.name in self.heapReads:
				self.heapReads[original.name] = replacement
			else:
				assert original.name in self.heapPsedoReads
				self.heapPsedoReads[original.name] = replacement
		#self.sanityCheck()

	def replaceDef(self, original, replacement):
		if isinstance(original, (LocalNode, ExistingNode)):
			assert isinstance(replacement, (LocalNode, ExistingNode)), replacement
			hit = replaceList(self.localModifies, original, replacement)
			assert hit, original
		else:
			assert original.name in self.heapModifies
			self.heapModifies[original.name] = replacement
		#self.sanityCheck()


	def addLocalRead(self, name, slot):
		assert isinstance(slot, (LocalNode, ExistingNode)), slot
		if name in self.localReads:
			assert self.localReads[name].canonical() is slot.canonical()
		else:
			slot = slot.addUse(self)
			self.localReads[name] = slot
		#self.sanityCheck()

	def addLocalModify(self, name, slot):
		assert isinstance(slot, LocalNode), slot
		slot = slot.addDefn(self)
		self.localModifies.append(slot)
		#self.sanityCheck()

	def addRead(self, name, slot):
		assert not isinstance(slot, (LocalNode, ExistingNode)), slot
		assert name not in self.heapReads
		slot = slot.addUse(self)
		self.heapReads[name] = slot
		#self.sanityCheck()

	def addModify(self, name, slot):
		assert not isinstance(slot, (LocalNode, ExistingNode)), slot
		assert name not in self.heapModifies
		slot = slot.addDefn(self)
		self.heapModifies[name] = slot
		#self.sanityCheck()

	def addPsedoRead(self, name, slot):
		assert not isinstance(slot,(LocalNode, ExistingNode)), slot
		assert name not in self.heapPsedoReads
		slot = slot.addUse(self)
		self.heapPsedoReads[name] = slot
		#self.sanityCheck()

	def __repr__(self):
		if self.predicates:
			return "op(%s)" % self.op.__class__.__name__
		else:
			return "op(%r)" % self.op

	def forward(self):
		return self.localModifies + self.heapModifies.values() + self.predicates

	def reverse(self):
		return [self.predicate] + self.localReads.values() + self.heapReads.values() + self.heapPsedoReads.values()


	def sanityCheck(self):
		for slot in self.localReads.itervalues():
			assert slot.isUse(self)
		for slot in self.heapReads.itervalues():
			assert slot.isUse(self)
		for slot in self.heapPsedoReads.itervalues():
			assert slot.isUse(self)

		for slot in self.localModifies:
			assert slot.isDefn(self)
		for slot in self.heapModifies.itervalues():
			assert slot.isDefn(self)

def refFromExisting(node):
	return node.annotation.references.merged[0]

class DataflowGraph(object):
	__slots__ = 'entry', 'exit', 'existing', 'null', 'entryPredicate'

	def __init__(self, hyperblock):
		self.entry    = Entry(hyperblock)
		self.exit     = None # Defer creation, as we don't know the hyperblock.
		self.existing = {}
		self.null     = NullNode()

		self.entryPredicate = PredicateNode(hyperblock, None, None, repr(hyperblock))
		self.entry.addEntry('*', self.entryPredicate)

	def getExisting(self, node):
		obj = node.object

		if obj not in self.existing:
			result = ExistingNode(obj, refFromExisting(node))
			self.existing[obj] = result
		else:
			result = self.existing[obj]
		return result