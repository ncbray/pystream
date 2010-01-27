from . base import Constraint

class CopyConstraint(Constraint):
	__slots__ = 'src', 'dst'
	def __init__(self, src, dst):
		assert src.isNode(), src
		assert dst.isNode(), dst

		Constraint.__init__(self)
		self.src = src
		self.dst = dst

	def attach(self):
		self.src.addNext(self)
		self.dst.addPrev(self)

	def makeConsistent(self, context):
		if self.src.values:
			self.changed(context, self.src, self.src.values)

	def changed(self, context, node, diff):
		self.dst.updateValues(diff)

	def __repr__(self):
		return "[CP %r -> %r]" % (self.src, self.dst)

	def isCopy(self):
		return True

class DownwardConstraint(Constraint):
	__slots__ = 'invoke', 'src', 'dst', 'fieldTransfer'
	def __init__(self, invoke, src, dst, fieldTransfer=False):
		assert src.isNode(), src
		assert dst.isNode(), dst

		Constraint.__init__(self)
		self.invoke = invoke
		self.src = src
		self.dst = dst
		self.fieldTransfer = fieldTransfer

	def attach(self):
		self.src.addNext(self)
		self.dst.addPrev(self)

	def makeConsistent(self, context):
		if self.src.values or (self.fieldTransfer and self.src.null):
			self.changed(context, self.src, self.src.values)

	def changed(self, context, node, diff):
		for obj in diff:
			self.dst.updateSingleValue(self.invoke.copyDown(obj))

		if self.fieldTransfer and self.src.null:
			self.dst.markNull()

	def __repr__(self):
		return "[DN %r -> %r]" % (self.src, self.dst)


class MemoryConstraint(Constraint):
	__slots__ = 'obj', 'fieldtype', 'field'

	def __init__(self, obj, fieldtype, field):
		Constraint.__init__(self)
		assert obj.isNode(), obj
		assert isinstance(fieldtype, str), fieldtype
		assert field.isNode(), field

		self.obj = obj
		self.fieldtype = fieldtype
		self.field = field

	def attach(self):
		self.obj.addNext(self)
		if self.field is not self.obj:
			self.field.addNext(self)

	def makeConsistent(self, context):
		if self.obj.values and self.field.values:
			self.changed(context, self.obj, self.obj.values)

	def changedDiffs(self, context, objDiff, fieldDiff):
		for obj in objDiff:
			for field in fieldDiff:
				self.concrete(context, obj, field)

	def changed(self, context, node, diff):
		if node is self.field:
			if node is self.obj:
				# must alias, values are correlated
				for value in diff:
					self.concrete(context, value, value)
			else:
				# field, and not object
				self.changedDiffs(context, self.obj.values, diff)
		elif node is self.obj:
			# object and not field
			self.changedDiffs(context, diff, self.field.values)
		# else is OK... for stores, changes to the value may cause this.

class LoadConstraint(MemoryConstraint):
	def __init__(self, obj, fieldtype, field, dst):
		assert dst.isNode(), dst
		MemoryConstraint.__init__(self, obj, fieldtype, field)
		self.dst   = dst

	def attach(self):
		MemoryConstraint.attach(self)
		self.dst.addPrev(self) # TODO is this correct?

	def concrete(self, context, obj, field):
		slot = context.field(obj, self.fieldtype, field.obj())
		context.assign(slot, self.dst)

	def __repr__(self):
		return "[LD %r %s %r -> %r]" % (self.obj, self.fieldtype, self.field, self.dst)

	def isLoad(self):
		return True

class CheckConstraint(MemoryConstraint):
	def __init__(self, obj, fieldtype, field, dst):
		assert dst.isNode(), dst
		MemoryConstraint.__init__(self, obj, fieldtype, field)
		self.dst   = dst

	def attach(self):
		MemoryConstraint.attach(self)
		self.dst.addPrev(self) # TODO is this correct?

	def concrete(self, context, obj, field):
		slot = context.field(obj, self.fieldtype, field.obj())
		context.constraint(ConcreteCheckConstraint(slot, self.dst))

	def __repr__(self):
		return "[CA %r %s %r -> %r]" % (self.obj, self.fieldtype, self.field, self.dst)


class ConcreteCheckConstraint(Constraint):
	def __init__(self, src, dst):
		assert src.isNode(), src
		assert dst.isNode(), dst
		Constraint.__init__(self)
		self.src   = src
		self.dst   = dst

		self.t = False
		self.f = False

	def attach(self):
		self.src.addNext(self)
		self.dst.addPrev(self)

	def makeConsistent(self, context):
		if self.src.values or self.src.null:
			self.changed(context, self.src, self.src.values)

	def changed(self, context, node, diff):
		if diff and not self.t:
			self.t = True
			self.dst.updateSingleValue(context.allocatePyObj(True))

		if self.src.null and not self.f:
			self.f = True
			self.dst.updateSingleValue(context.allocatePyObj(False))

	def __repr__(self):
		return "[CC %r -> %r]" % (self.src, self.dst)



class StoreConstraint(MemoryConstraint):
	def __init__(self, src, obj, fieldtype, field):
		assert src.isNode(), src
		MemoryConstraint.__init__(self, obj, fieldtype, field)
		self.src = src

	def attach(self):
		MemoryConstraint.attach(self)
		if self.src is not self.obj and self.src is not self.field:
			self.src.addNext(self) # TODO is this correct?

	def concrete(self, context, obj, field):
		slot = context.field(obj, self.fieldtype, field.obj())
		context.assign(self.src, slot)

	def __repr__(self):
		return "[ST %r -> %r %s %r]" % (self.src, self.obj, self.fieldtype, self.field)

	def isStore(self):
		return True
