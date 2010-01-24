from . base import Constraint

class CopyConstraint(Constraint):
	__slots__ = 'src', 'dst'
	def __init__(self, src, dst):
		assert src.isNode(), src
		assert dst.isNode(), dst

		Constraint.__init__(self)
		self.src = src
		self.dst = dst

		self.attach()
		self.makeConsistent()

	def attach(self):
		self.src.addCallback(self.srcChanged)

	def makeConsistent(self):
		# Make constraint consistent
		if self.src.values:
			self.srcChanged(self.src.values)

	def srcChanged(self, diff):
		self.dst.updateValues(diff)

	def __repr__(self):
		return "[%r -> %r]" % (self.src, self.dst)

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

		self.attach()
		self.makeConsistent()

	def attach(self):
		self.src.addCallback(self.srcChanged)

	def makeConsistent(self):
		# Make constraint consistent
		if self.src.values or (self.fieldTransfer and self.src.null):
			self.srcChanged(self.src.values)

	def srcChanged(self, diff):
		for obj in diff:
			self.dst.updateSingleValue(self.invoke.copyDown(obj))

		if self.fieldTransfer and self.src.null:
			self.dst.markNull()

	def __repr__(self):
		return "[DN %r -> %r]" % (self.src, self.dst)


class LoadConstraint(Constraint):
	def __init__(self, src, fieldtype, field, dst):
		assert src.isNode(), src
		assert isinstance(fieldtype, str), fieldtype
		assert field.isNode(), field
		assert dst.isNode(), dst

		Constraint.__init__(self)
		self.src   = src
		self.fieldtype = fieldtype
		self.field = field
		self.dst   = dst

		self.attach()
		self.makeConsistent()

	# HACK
	@property
	def context(self):
		return self.dst.context

	def attach(self):
		self.src.addCallback(self.srcChanged)
		self.field.addCallback(self.fieldChanged)

	def makeConsistent(self):
		# Make constraint consistent
		if self.src.values and self.field.values:
			self.srcChanged(self.src.values)

	def concrete(self, obj, field):
		slot = self.context.field(obj, self.fieldtype, field.xtype.obj)
		self.context.assign(slot, self.dst)

	def srcChanged(self, diff):
		for obj in diff:
			for field in self.field.values:
				self.concrete(obj, field)

	def fieldChanged(self, diff):
		for obj in self.src.values:
			# Avoid problems if src and field alias...
			if self.src is self.field and obj in diff: continue

			for field in diff:
				self.concrete(obj, field)

	def __repr__(self):
		return "[%s %r.%r -> %r]" % (self.fieldtype, self.src, self.field, self.dst)


class CheckConstraint(Constraint):
	def __init__(self, context, src, fieldtype, field, dst):
		assert src.isNode(), src
		assert isinstance(fieldtype, str), fieldtype
		assert field.isNode(), field
		assert dst.isNode(), dst

		Constraint.__init__(self)
		self.context = context
		self.src   = src
		self.fieldtype = fieldtype
		self.field = field
		self.dst   = dst

		self.attach()
		self.makeConsistent()

	def attach(self):
		self.src.addCallback(self.srcChanged)
		self.field.addCallback(self.fieldChanged)

	def makeConsistent(self):
		# Make constraint consistent
		if self.src.values and self.field.values:
			self.srcChanged(self.src.values)

	def concrete(self, obj, field):
		slot = self.context.field(obj, self.fieldtype, field.xtype.obj)
		self.context.constraint(ConcreteCheckConstraint(self.context, slot, self.dst))

	def srcChanged(self, diff):
		for obj in diff:
			for field in self.field.values:
				self.concrete(obj, field)

	def fieldChanged(self, diff):
		for obj in self.src.values:
			# Avoid problems if src and field alias...
			if self.src is self.field and obj in diff: continue

			for field in diff:
				self.concrete(obj, field)

	def __repr__(self):
		return "[%s %r.%r CHECK=> %r]" % (self.fieldtype, self.src, self.field, self.dst)


class ConcreteCheckConstraint(Constraint):
	def __init__(self, context, src, dst):
		assert src.isNode(), src
		assert dst.isNode(), dst
		Constraint.__init__(self)
		self.context = context
		self.src   = src
		self.dst   = dst

		self.t = False
		self.f = False

		self.attach()
		self.makeConsistent()

	def attach(self):
		self.src.addCallback(self.srcChanged)

	def makeConsistent(self):
		if self.src.values or self.src.null:
			self.srcChanged(self.src.values)

	def srcChanged(self, diff):
		if diff and not self.t:
			self.t = True
			self.dst.updateSingleValue(self.context.allocatePyObj(True))

		if self.src.null and not self.f:
			self.f = True
			self.dst.updateSingleValue(self.context.allocatePyObj(False))


class StoreConstraint(Constraint):
	def __init__(self, src, dst, fieldtype, field):
		assert src.isNode(), src
		assert dst.isNode(), dst
		assert isinstance(fieldtype, str), fieldtype
		assert field.isNode(), field
		Constraint.__init__(self)
		self.src   = src
		self.dst   = dst
		self.fieldtype = fieldtype
		self.field = field

		self.attach()
		self.makeConsistent()

	def attach(self):
		self.dst.addCallback(self.dstChanged)
		self.field.addCallback(self.fieldChanged)

	def makeConsistent(self):
		# Make constraint consistent
		if self.dst.values and self.field.values:
			self.dstChanged(self.dst.values)

	def dstChanged(self, diff):
		assert False

	def fieldChanged(self, diff):
		# TODO field is dst
		pass

	def __repr__(self):
		return "[%s %r -> %r.%r]" % (self.fieldtype, self.src, self.dst, self.field)
