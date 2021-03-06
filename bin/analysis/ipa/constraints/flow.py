# Copyright 2011 Nicholas Bray
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import itertools
from . base import Constraint
from . import qualifiers

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

		if self.src.critical.values:
			self.criticalChanged(context, self.src, self.src.critical.values)

	def changed(self, context, node, diff):
		self.dst.updateValues(diff)

	def __repr__(self):
		return "[CP %r -> %r]" % (self.src, self.dst)

	def isCopy(self):
		return True

	def criticalChanged(self, context, node, diff):
		self.dst.critical.updateValues(context, self.dst, diff)


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

		# Critical values are not transfered.

	def changed(self, context, node, diff):
		for obj in diff:
			self.dst.updateSingleValue(self.invoke.copyDown(obj))

		if self.fieldTransfer and self.src.null:
			self.dst.markNull()

	def __repr__(self):
		return "[DN %r -> %r]" % (self.src, self.dst)


class MemoryConstraint(Constraint):
	__slots__ = 'obj', 'fieldtype', 'field', 'criticalOp'

	def __init__(self, obj, fieldtype, field):
		Constraint.__init__(self)
		assert obj.isNode(), obj
		assert isinstance(fieldtype, str), fieldtype
		assert field.isNode(), field

		self.obj = obj
		self.fieldtype = fieldtype
		self.field = field
		self.criticalOp = False

	def attach(self):
		self.obj.addNext(self)
		if self.field is not self.obj:
			self.field.addNext(self)

	def makeConsistent(self, context):
		if self.obj.values and self.field.values:
			self.changed(context, self.obj, self.obj.values)

		if self.obj.critical.values:
			self.criticalChanged(context, self.obj, self.obj.critical.values)


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
	__slots__ = 'dst',

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

	def criticalChanged(self, context, node, diff):
		if not self.criticalOp and diff:
			self.criticalOp = True
			self.dst.critical.markCritical(context, self.dst)


class CheckConstraint(MemoryConstraint):
	__slots__ = 'dst',

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

	def criticalChanged(self, context, node, diff):
		pass


class ConcreteCheckConstraint(Constraint):
	__slots__ = 'src', 'dst', 't', 'f'

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

	def criticalChanged(self, context, node, diff):
		pass


class StoreConstraint(MemoryConstraint):
	__slots__ = 'src',

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

	def criticalChanged(self, context, node, diff):
		if not self.criticalOp and diff:
			self.criticalOp = True
			context.criticalStore(self)


class AllocateConstraint(Constraint):
	__slots__ = 'op', 'src', 'dst'
	def __init__(self, op, src, dst):
		Constraint.__init__(self)
		self.op  = op
		self.src = src
		self.dst = dst

	def attach(self):
		self.src.addNext(self)
		self.dst.addPrev(self)

	def makeConsistent(self, context):
		if self.src.values:
			self.changed(context, self.src, self.src.values)

	def changed(self, context, node, diff):
		for value in diff:
			assert value.obj().pythonType() is type, value
			exinst = context.analysis.pyObjInst(value.pyObj())
			xtype = context.analysis.canonical.pathType(None, exinst, node)
			inst   = context.analysis.objectName(xtype, qualifiers.HZ)

			self.dst.updateSingleValue(inst)

	def __repr__(self):
		return "[AL %r -> %r]" % (self.src, self.dst)

	def isAllocate(self):
		return True

	def criticalChanged(self, context, node, diff):
		pass

class IsConstraint(Constraint):
	__slots__ = 'left', 'right', 'dst', 't', 'f'

	def __init__(self, left, right, dst):
		Constraint.__init__(self)
		self.left  = left
		self.right = right
		self.dst   = dst

		self.t = False
		self.f = False

	def attach(self):
		self.left.addNext(self)
		if self.left is not self.right:
			self.right.addNext(self)
		self.dst.addPrev(self)

	def makeConsistent(self, context):
		if self.left.values and self.right.values:
			self.changed(context, self.left, self.left.values)

	def canBeTrue(self, context):
		if not self.t:
			self.t = True
			self.dst.updateSingleValue(context.allocatePyObj(True))

	def canBeFalse(self, context):
		if not self.f:
			self.f = True
			self.dst.updateSingleValue(context.allocatePyObj(False))

	def concrete(self, context, left, right):
		# TODO use regions for even more precision?
		# TODO use qualifiers for non-CI types
		lxtype = left.xtype
		rxtype = left.xtype

		lpt = lxtype.obj.pythonType()
		rpt = rxtype.obj.pythonType()

		if lpt is not rpt:
			self.canBeFalse(context)
		elif lxtype.isExisting() and rxtype.isExisting():
			if lxtype.obj is rxtype.obj:
				self.canBeTrue(context)
			else:
				self.canBeFalse(context)
		elif isinstance(lpt, xtypes.ConstantTypes):
			# May be pooled later, which creates ambiguity
			self.canBeTrue(context)
			self.canBeFalse(context)
		elif lxtype is rxtype:
			# More that one of this object may be created...
			self.canBeTrue(context)
			self.canBeFalse(context)
		else:
			# Not the same object, will not be pooled.
			self.canBeFalse(context)

	def done(self):
		return self.t and self.f

	def changed(self, context, node, diff):
		if self.done(): return

		if node is self.left:
			if node is self.right:
				for value in diff:
					self.concrete(context, value, value)
					if self.done(): return
			else:
				for left, right in itertools.product(diff, self.right.values):
					self.concrete(context, left, right)
					if self.done(): return

		elif node is self.right:
			for left, right in itertools.product(self.left.values, diff):
				self.concrete(context, left, right)
				if self.done(): return

	def __repr__(self):
		return "[IS %r %r -> %r]" % (self.left, self.right, self.dst)

	def criticalChanged(self, context, node, diff):
		pass
