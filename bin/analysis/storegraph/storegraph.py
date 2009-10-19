from . import extendedtypes
from . import setmanager

# HACK for assertions
from language.python import program

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

	def isObjectContext(self):
		return False

# This corresponds to a group of nodes, such as in a function or in a program,
# depending on how the analysis works.
class StoreGraph(MergableNode):
	__slots__ = 'slots', 'regionHint', 'setManager', 'extractor', 'canonical', 'typeSlotName', 'lengthSlotName'

	def __init__(self, extractor, canonical):
		MergableNode.__init__(self)

		# Root slots, such as locals and references to "existing" objects
		self.slots      = {}
		self.regionHint = RegionNode(self)
		self.setManager = setmanager.CachedSetManager()
		self.extractor  = extractor
		self.canonical  = canonical

		# HACK this should be centeralized?
		self.typeSlotName = self.canonical.fieldName('LowLevel', self.extractor.getObject('type'))
		self.lengthSlotName = self.canonical.fieldName('LowLevel', self.extractor.getObject('length'))


	def existingSlotRef(self, xtype, slotName):
		assert xtype.isExisting()
		assert not slotName.isRoot()

		obj = xtype.obj
		assert isinstance(obj, program.AbstractObject), obj
		self.extractor.ensureLoaded(obj)

		slottype, key = slotName.type, slotName.name
		assert isinstance(key, program.AbstractObject), key

		if isinstance(obj, program.Object):
			if slottype == 'LowLevel':
				subdict = obj.lowlevel
			elif slottype == 'Attribute':
				subdict = obj.slot
			elif slottype == 'Array':
				# HACK
				if isinstance(obj.pyobj, list):
					return set([self.canonical.existingType(t) for t in obj.array.itervalues()])

				subdict = obj.array
			elif slottype == 'Dictionary':
				subdict = obj.dictionary
			else:
				assert False, slottype

			if key in subdict:
				return (self.canonical.existingType(subdict[key]),)

		# Not found
		return None

	def setTypePointer(self, obj):
		xtype = obj.xtype

		if not xtype.isExisting():
			# Makes sure the type pointer is valid.
			self.extractor.ensureLoaded(xtype.obj)

			# Get the type object
			typextype = self.canonical.existingType(xtype.obj.type)

			field = obj.field(self.typeSlotName, self.regionHint)
			field.initializeType(typextype)

	def root(self, slotName, regionHint=None):
		self = self.getForward()

		if slotName not in self.slots:
			assert slotName.isRoot(), slotName
			region = self.regionHint if regionHint is None else regionHint
			root = SlotNode(None, slotName, region, self.setManager.empty())
			self.slots[slotName] = root
			return root
		else:
			# TODO merge region?
			return self.slots[slotName]

	def __iter__(self):
		return self.slots.itervalues()

	def removeObservers(self):
		processed = set()
		for slot in self:
			slot.removeObservers(processed)

class RegionNode(MergableNode):
	__slots__ = 'objects', 'group', 'weight'

	def __init__(self, group):
		assert group is not None
		MergableNode.__init__(self)

		self.group   = group

		self.objects = {}
		self.weight  = 0

	def merge(self, other):
		self  = self.getForward()
		other = other.getForward()

		if self != other:
			other.setForward(self)

			objects = other.objects
			other.objects = None

			for xtype, obj in objects.iteritems():
				if xtype in self.objects:
					self.objects[xtype] = self.objects[xtype].merge(obj)
				else:
					self.objects[xtype] = obj

				self = self.getForward()

		return self

	def object(self, xtype):
		self = self.getForward()

		if xtype not in self.objects:
			obj = ObjectNode(self, xtype)
			self.objects[xtype] = obj

			# Note this is done after setting the dictionary,
			# as this call can recurse.
			self.group.setTypePointer(obj)

			return obj
		else:
			return self.objects[xtype]

	def __iter__(self):
		self = self.getForward()
		return self.objects.itervalues()


class ObjectNode(MergableNode):
	__slots__ = 'region', 'xtype', 'slots', 'leaks', 'annotation'
	def __init__(self, region, xtype):
		MergableNode.__init__(self)

		assert isinstance(xtype, extendedtypes.ExtendedType), type(xtype)
		self.region = region
		self.xtype  = xtype
		self.slots  = {}
		self.leaks  = True

	def merge(self, other):
		self  = self.getForward()
		other = other.getForward()

		if self != other:
			other.setForward(self)

			slots = other.slots
			other.slots = None

			for fieldName, field in slots.iteritems():
				if fieldName in self.slots:
					self.slots[fieldName] = self.slots[fieldName].merge(field)
				else:
					self.slots[fieldName] = field

				self = self.getForward()

		self.region = self.region.getForward()
		return self

	def field(self, slotName, regionHint):
		if slotName not in self.slots:
			assert not slotName.isRoot()

			if regionHint is None:
				assert False
				region = RegionNode(self.region.group)
			else:
				region = regionHint

			group = region.group
			field = SlotNode(self, slotName, region, group.setManager.empty())
			self.slots[slotName] = field

			if self.xtype.isExisting():
				ref = group.existingSlotRef(self.xtype, slotName)
				if ref is not None:
					field.initializeTypes(ref)
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

	def removeObservers(self, processed):
		self = self.getForward()
		if self not in processed:
			processed.add(self)

			for ref in self:
				ref.removeObservers(processed)

	def isObjectContext(self):
		return True

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

	def merge(self, other):
		self  = self.getForward()
		other = other.getForward()

		if self != other:
			other.setForward(self)

			refs = other.refs
			other.refs = None

			observers = other.observers
			other.observers = None

			# May merge
			self.region = self.region.merge(other.region)
			self = self.getForward()

			group = self.region.group
			sdiff = group.setManager.diff(refs, self.refs)
			odiff = group.setManager.diff(self.refs, refs)


			if sdiff or (not self.null and other.null):
				self._update(sdiff)

			self.observers.extend(observers)

			if odiff or (self.null and not other.null):
				for o in observers:
					o.mark()

			# Merge flags
			self.null |= other.null

		self.region = self.region.getForward()
		self.object = self.object.getForward()

		return self

	def initializeTypes(self, xtypes):
		for xtype in xtypes:
			self.initializeType(xtype)

	def initializeType(self, xtype):
		assert isinstance(xtype, extendedtypes.ExtendedType), type(xtype)

		self = self.getForward()

		# TODO use diffTypeSet from canonicalSlots?
		if xtype not in self.refs:
			self._update(frozenset((xtype,)))
			self.null = False

		# Ensure the object exists
		return self.region.object(xtype)


	def update(self, other):
		self = self.getForward()

		if self.region != other.region:
			self.region = self.region.merge(other.region)

			self  = self.getForward()
			self.region  = self.region.getForward()

			other = other.getForward()
			other.region = other.region.getForward()

		assert self.region == other.region, (self.region, other.region)

		group = self.region.group
		diff = group.setManager.diff(other.refs, self.refs)
		if diff: self._update(diff)

		return self

	def _update(self, diff):
		group = self.region.group
		self.refs = group.setManager.inplaceUnion(self.refs, diff)
		for o in self.observers:
			o.mark()

	def dependsRead(self, constraint):
		self = self.getForward()
		self.observers.append(constraint)
		if self.refs: constraint.mark()

	def dependsWrite(self, constraint):
		self = self.getForward()
		self.observers.append(constraint)
		if self.refs: constraint.mark()

	def __iter__(self):
		self = self.getForward()

		# HACK use setManager.iter?
		for xtype in self.refs:
			yield self.region.object(xtype)

	def __repr__(self):
		self = self.getForward()

		xtype = None if self.object is None else self.object.xtype
		return "slot(%r, %r)" % (xtype, self.slotName)

	def removeObservers(self, processed):
		self = self.getForward()
		if self not in processed:
			processed.add(self)
			self.observers = []

			for ref in self:
				ref.removeObservers(processed)