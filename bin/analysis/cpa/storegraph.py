from . import extendedtypes

class RegionGroup(object):
	__slots__ = 'slots'
	def __init__(self):
		# Root slots, such as locals and references to "existing" objects
		self.slots = {}

	def root(self, sys, slot, targetRegion):
		if slot not in self.slots:
			assert slot.isRoot(), slot
			root = SlotNode(None, slot, targetRegion, sys.slotManager.emptyTypeSet())
			self.slots[slot] = root
			return root
		else:
			# TODO merge region?
			return self.slots[slot]

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

	def __iter__(self):
		return self.objects.itervalues()


class ObjectNode(object):
	__slots__ = 'region', 'xtype', 'slots'
	def __init__(self, region, xtype):
		assert isinstance(xtype, extendedtypes.ExtendedType), type(xtype)
		self.region = region
		self.xtype  = xtype
		self.slots = {}

	def field(self, sys, slotName, targetRegion):
		if slotName not in self.slots:
			assert not slotName.isRoot()
			field = SlotNode(self, slotName, targetRegion, sys.slotManager.emptyTypeSet())
			self.slots[slotName] = field

			if self.xtype.isExisting():
				data = sys.slotManager.existingSlot(self.xtype, slotName)
				if data: field.initialize(sys, *data)
			return field
		else:
			# TODO merge region?
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

	def initialize(self, sys, obj):
		xtype = obj.xtype
		self.initializeType(sys, xtype)

	def initializeType(self, sys, xtype):
		assert isinstance(xtype, extendedtypes.ExtendedType), type(xtype)
		if xtype not in self.refs:
			self._update(sys, frozenset((xtype,)))

	def update(self, sys, other):
		assert self.region == other.region
		diff = other.refs-self.refs
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

	def __iter__(self):
		for xtype in self.refs:
			yield self.region.object(None, xtype) # HACK

	def __repr__(self):
		xtype = None if self.object is None else self.object.xtype
		return "slot(%r, %r)" % (xtype, self.slotName)