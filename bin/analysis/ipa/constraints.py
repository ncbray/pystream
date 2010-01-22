from language.python import ast
from analysis.storegraph import extendedtypes

import itertools

HZ = 'HZ'
DN = 'DN'
UP = 'UP'
GLBL = 'GLBL'

class ConstraintNode(object):
	def __init__(self, context, name, values=None, ci=False):
		self.context = context
		self.name = name
		self.ci = ci

		if values is not None:
			for value in values: assert isinstance(value, AnalysisObject), value
			self.values = context.analysis.setmanager.coerce(values)
		else:
			self.values = context.analysis.setmanager.empty()
		self.diff = context.analysis.setmanager.empty()

		self.dirty = False

		self.callbacks = []

	def markParam(self):
		pass

	def markReturn(self):
		pass

	def addCallback(self, callback):
		self.callbacks.append(callback)

	def updateValues(self, values):
		sm = self.context.analysis.setmanager
		# Not retained, so set manager is not used
		diff = sm.tempDiff(values, self.values)

		if diff:
			for value in diff:
				assert isinstance(value, AnalysisObject), value

			self.diff = sm.inplaceUnion(self.diff, diff)
			if not self.dirty:
				self.dirty = True
				self.context.dirtySlot(self)
			return True
		else:
			return False

	def propagate(self):
		assert self.dirty
		self.dirty = False

		# Update the sets of objects
		# Must be done before any callback is performed, as a
		# cyclic dependency could update these values
		sm = self.context.analysis.setmanager
		diff = self.diff
		self.values = sm.inplaceUnion(self.values, diff)
		self.diff   = sm.empty()

		for callback in self.callbacks:
			callback(diff)

	def __repr__(self):
		return "slot(%r/%d)" % (self.name, id(self))


class AnalysisObject(object):
	__slots__ = 'name', 'qualifier'
	def __init__(self, name, qualifier):
		assert isinstance(name, extendedtypes.ExtendedType), name
		self.name = name
		self.qualifier = qualifier

	def __repr__(self):
		return "ao(%r/%d)" % (self.name, id(self))

class Constraint(object):
	__slots__ = 'qualifier', 'dirty'
	def __init__(self):
		self.qualifier = HZ
		self.dirty     = True


class CopyConstraint(Constraint):
	def __init__(self, src, dst):
		assert isinstance(src, ConstraintNode), src
		assert isinstance(dst, ConstraintNode), dst
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
		return "[%s %r -> %r]" % (self.qualifier, self.src, self.dst)


class FilteredCopyConstraint(Constraint):
	def __init__(self, src, typeFilter, dst):
		assert isinstance(src, ConstraintNode), src
		assert isinstance(typeFilter, extendedtypes.ExtendedType), typeFilter
		assert isinstance(dst, ConstraintNode), dst
		Constraint.__init__(self)
		self.src    = src
		self.typeFilter = typeFilter
		self.dst    = dst

		self.attach()
		self.makeConsistent()

	def attach(self):
		self.src.addCallback(self.srcChanged)

	def makeConsistent(self):
		# Make constraint consistent
		if self.src.values:
			self.srcChanged(self.src.values)

	def srcChanged(self, diff):
		filtered = []

		# TODO make the obj and filter types consistent?

		for obj in diff:
			assert isinstance(obj, AnalysisObject), obj
			if obj.name.cpaType() is self.typeFilter:
				filtered.append(obj)

		if filtered:
			self.dst.updateValues(frozenset(filtered))

	def __repr__(self):
		return "[%s %r %r -> %r]" % (self.qualifier, self.typeFilter, self.src,  self.dst)


class LoadConstraint(Constraint):
	def __init__(self, src, fieldtype, field, dst):
		assert isinstance(src, ConstraintNode), src
		assert isinstance(fieldtype, str), fieldtype
		assert isinstance(field, ConstraintNode), field
		assert isinstance(dst, ConstraintNode), dst
		Constraint.__init__(self)
		self.src   = src
		self.fieldtype = fieldtype
		self.field = field
		self.dst   = dst

		self.src.addCallback(self.srcChanged)
		self.field.addCallback(self.fieldChanged)

		# Make constraint consistent
		if self.src.values and self.field.values:
			self.srcChanged(self.src.values)

	def srcChanged(self, diff):
		pass

	def fieldChanged(self, diff):
		# TODO field is src
		pass

	def __repr__(self):
		return "[%s %s %r.%r -> %r]" % (self.qualifier, self.fieldtype, self.src, self.field, self.dst)


class CheckConstraint(Constraint):
	def __init__(self, src, fieldtype, field, dst):
		assert isinstance(src, ConstraintNode), src
		assert isinstance(fieldtype, str), fieldtype
		assert isinstance(field, ConstraintNode), field
		assert isinstance(dst, ConstraintNode), dst
		Constraint.__init__(self)
		self.src   = src
		self.fieldtype = fieldtype
		self.field = field
		self.dst   = dst

		self.src.addCallback(self.srcChanged)
		self.field.addCallback(self.fieldChanged)

		# Make constraint consistent
		if self.src.values and self.field.values:
			self.srcChanged(self.src.values)

	def srcChanged(self, diff):
		pass

	def fieldChanged(self, diff):
		# TODO field is src
		pass

	def __repr__(self):
		return "[%s %s %r.%r CHECK=> %r]" % (self.qualifier, self.fieldtype, self.src, self.field, self.dst)


class StoreConstraint(Constraint):
	def __init__(self, src, dst, fieldtype, field):
		assert isinstance(src, ConstraintNode), src
		assert isinstance(dst, ConstraintNode), dst
		assert isinstance(fieldtype, str), fieldtype
		assert isinstance(field, ConstraintNode), field
		Constraint.__init__(self)
		self.src   = src
		self.dst   = dst
		self.fieldtype = fieldtype
		self.field = field

		self.dst.addCallback(self.dstChanged)
		self.field.addCallback(self.fieldChanged)

		# Make constraint consistent
		if self.dst.values and self.field.values:
			self.dstChanged(self.dst.values)

	def dstChanged(self, diff):
		pass

	def fieldChanged(self, diff):
		# TODO field is dst
		pass

	def __repr__(self):
		return "[%s %s %r -> %r.%r]" % (self.qualifier, self.fieldtype, self.src, self.dst, self.field)
