from . import extendedtypes

class RegionGroup(object):
	__slots__ = 'slots'
	def __init__(self):
		# Root slots, such as locals and references to "existing" objects
		self.slots = {}

	def root(self, sys, slotName, regionHint):
		if slotName not in self.slots:
			assert slotName.isRoot(), slot
			root = SlotNode(None, slotName, regionHint, sys.slotManager.emptyTypeSet())
			self.slots[slotName] = root
			return root
		else:
			# TODO merge region?
			return self.slots[slotName]

	def knownRoot(self, slotName):
		return self.slots[slotName]

	def __iter__(self):
		return self.slots.itervalues()


class RegionNode(object):
	__slots__ = 'objects', 'group', 'forward', 'weight'

	def __init__(self, group):
		self.objects = {}

		self.group   = group
		self.forward = None
		self.weight  = 0

	def object(self, sys, xtype):
		if xtype not in self.objects:
			obj = ObjectNode(self, xtype)
			self.objects[xtype] = obj

			# Note this is done after setting the dictionary,
			# as this call can recurse.
			sys.setTypePointer(obj)

			return obj
		else:
			return self.objects[xtype]

	def knownObject(self, xtype):
		return self.objects[xtype]

	def __iter__(self):
		return self.objects.itervalues()


class ObjectNode(object):
	__slots__ = 'region', 'xtype', 'slots'
	def __init__(self, region, xtype):
		assert isinstance(xtype, extendedtypes.ExtendedType), type(xtype)
		self.region = region
		self.xtype  = xtype
		self.slots = {}

	def field(self, sys, slotName, regionHint):
		assert sys is not None
		if slotName not in self.slots:
			assert not slotName.isRoot()
			field = SlotNode(self, slotName, regionHint, sys.slotManager.emptyTypeSet())
			self.slots[slotName] = field

			if self.xtype.isExisting():
				ref = sys.slotManager.existingSlotRef(self.xtype, slotName)
				if ref is not None:
					field.initializeType(sys, ref)
			return field
		else:
			# TODO merge region?
			return self.slots[slotName]

	def knownField(self, slotName):
		return self.slots[slotName]

	def __iter__(self):
		return self.slots.itervalues()


class SlotNode(object):
	__slots__ = 'object', 'slotName', 'region', 'refs', 'observers'
	def __init__(self, object, slot, region, refs):
		self.object    = object
		self.slotName  = slot
		self.region    = region
		self.refs      = refs
		self.observers = []

	def initializeType(self, sys, xtype):
		assert sys is not None
		assert isinstance(xtype, extendedtypes.ExtendedType), type(xtype)

		# TODO use diffTypeSet from canonicalSlots?
		if xtype not in self.refs:
			self._update(sys, frozenset((xtype,)))
			self.region.object(sys, xtype) # Ensure the object exists

	def update(self, sys, other):
		assert sys is not None
		assert self.region == other.region
		diff = sys.slotManager.diffTypeSet(other.refs, self.refs)
		if diff: self._update(sys, diff)

	def _update(self, sys, diff):
		self.refs = sys.slotManager.inplaceUnionTypeSet(self.refs, diff)
		for o in self.observers:
			o.mark(sys)

	def dependsRead(self, sys, constraint):
		self.observers.append(constraint)
		if self.refs: constraint.mark(sys)

	def dependsWrite(self, sys, constraint):
		self.observers.append(constraint)
		if self.refs: constraint.mark(sys)

	def knownObject(self, xtype):
		return self.region.knownObject(xtype)

	def __iter__(self):
		# HACK use slotManager.iterTypeSet?
		for xtype in self.refs:
			yield self.region.knownObject(xtype)

	def __repr__(self):
		xtype = None if self.object is None else self.object.xtype
		return "slot(%r, %r)" % (xtype, self.slotName)