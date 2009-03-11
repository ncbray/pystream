from . import extendedtypes


class MergableNode(object):
	__slots__ = 'forward'

	def __init__(self):
		self.forward = None

	def getForward(self):
		if self.forward:
			forward = self.forward.getForward()
			self.forward = forward
			return forward
		else:
			return self

	def setForward(self, other):
		assert self.forward is None
		assert other.forward is None
		self.forward = other

class RegionGroup(MergableNode):
	__slots__ = 'slots', 'regionHint'

	def __init__(self):
		MergableNode.__init__(self)

		# Root slots, such as locals and references to "existing" objects
		self.slots   = {}
		self.regionHint = RegionNode(self)

	def root(self, sys, slotName, regionHint):
		self = self.getForward()

		if slotName not in self.slots:
			assert slotName.isRoot(), slot
			if regionHint is None:
				assert False
				region = RegionNode(self)
			else:
				region = regionHint
			root = SlotNode(None, slotName, region, sys.setManager.empty())
			self.slots[slotName] = root
			return root
		else:
			# TODO merge region?
			return self.slots[slotName]

	def knownRoot(self, slotName):
		return self.slots[slotName]

	def __iter__(self):
		return self.slots.itervalues()


class RegionNode(MergableNode):
	__slots__ = 'objects', 'group', 'weight'

	def __init__(self, group):
		assert group is not None
		MergableNode.__init__(self)

		self.group   = group

		self.objects = {}
		self.weight  = 0

	def merge(self, sys, other):
		self  = self.getForward()
		other = other.getForward()

		if self != other:
			other.setForward(self)

			objects = other.objects
			other.objects = None

			for xtype, obj in objects.iteritems():
				if xtype in self.objects:
					self.objects[xtype] = self.objects[xtype].merge(sys, obj)
				else:
					self.objects[xtype] = obj

				self = self.getForward()

		return self

	def object(self, sys, xtype):
		self = self.getForward()

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
		self = self.getForward()
		return self.objects[xtype]

	def __iter__(self):
		self = self.getForward()
		return self.objects.itervalues()


class ObjectNode(MergableNode):
	__slots__ = 'region', 'xtype', 'slots', 'leaks'
	def __init__(self, region, xtype):
		MergableNode.__init__(self)

		assert isinstance(xtype, extendedtypes.ExtendedType), type(xtype)
		self.region = region
		self.xtype  = xtype
		self.slots  = {}
		self.leaks  = True

	def merge(self, sys, other):
		self  = self.getForward()
		other = other.getForward()

		if self != other:
			other.setForward(self)

			slots = other.slots
			other.slots = None

			for fieldName, field in slots.iteritems():
				if fieldName in self.slots:
					self.slots[fieldName] = self.slots[fieldName].merge(sys, field)
				else:
					self.slots[fieldName] = obj

				self = self.getForward()

		self.region = self.region.getForward()
		return self

	def field(self, sys, slotName, regionHint):
		if slotName not in self.slots:
			assert not slotName.isRoot()

			if regionHint is None:
				assert False
				region = RegionNode(self.region.group)
			else:
				region = regionHint

			field = SlotNode(self, slotName, region, sys.setManager.empty())
			self.slots[slotName] = field

			if self.xtype.isExisting():
				ref = sys.existingSlotRef(self.xtype, slotName)
				if ref is not None:
					field.initializeTypes(sys, ref)
			return field
		else:
			# TODO merge region?
			return self.slots[slotName]

	def knownField(self, slotName):
		return self.slots[slotName]

	def __iter__(self):
		return self.slots.itervalues()

	def __repr__(self):
		return "obj(%r, %r)" % (self.xtype, id(self.region))

class SlotNode(MergableNode):
	__slots__ = 'object', 'slotName', 'region', 'refs', 'null', 'observers'
	def __init__(self, object, slot, region, refs):
		MergableNode.__init__(self)

		self.object    = object
		self.slotName  = slot
		self.region    = region
		self.refs      = refs
		self.null      = True
		self.observers = []

	def merge(self, sys, other):
		self  = self.getForward()
		other = other.getForward()

		if self != other:
			other.setForward(self)

			refs = other.refs
			other.refs = None

			observers = other.observers
			other.observers = None

			# May merge
			self.region = self.region.merge(sys, other.region)
			self = self.getForward()

			sdiff = sys.setManager.diff(refs, self.refs)
			odiff = sys.setManager.diff(self.refs, refs)


			if sdiff or (not self.null and other.null):
				self._update(sys, sdiff)

			self.observers.extend(observers)

			if odiff or (self.null and not other.null):
				for o in observers:
					o.mark(sys)

			# Merge flags
			self.null |= other.null

		self.region = self.region.getForward()
		self.object = self.object.getForward()

		return self

	def initializeTypes(self, sys, xtypes):
		for xtype in xtypes:
			self.initializeType(sys, xtype)

	def initializeType(self, sys, xtype):
		self = self.getForward()


		assert isinstance(xtype, extendedtypes.ExtendedType), type(xtype)

		# TODO use diffTypeSet from canonicalSlots?
		if xtype not in self.refs:
			self._update(sys, frozenset((xtype,)))
			self.null = False

		# Ensure the object exists
		return self.region.object(sys, xtype)


	def update(self, sys, other):
		self = self.getForward()

		if self.region != other.region:
			self.region = self.region.merge(sys, other.region)

			self  = self.getForward()
			self.region  = self.region.getForward()

			other = other.getForward()
			other.region = other.region.getForward()

		assert self.region == other.region, (self.region, other.region)


		diff = sys.setManager.diff(other.refs, self.refs)
		if diff: self._update(sys, diff)

	def _update(self, sys, diff):
		self.refs = sys.setManager.inplaceUnion(self.refs, diff)
		for o in self.observers:
			o.mark(sys)

	def dependsRead(self, sys, constraint):
		self = self.getForward()

		self.observers.append(constraint)
		if self.refs: constraint.mark(sys)

	def dependsWrite(self, sys, constraint):
		self = self.getForward()

		self.observers.append(constraint)
		if self.refs: constraint.mark(sys)

	def knownObject(self, xtype):
		self = self.getForward()

		return self.region.knownObject(xtype)

	def __iter__(self):
		self = self.getForward()

		# HACK use setManager.iter?
		for xtype in self.refs:
			yield self.region.knownObject(xtype)

	def __repr__(self):
		self = self.getForward()

		xtype = None if self.object is None else self.object.xtype
		return "slot(%r, %r)" % (xtype, self.slotName)