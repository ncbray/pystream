from language.python import ast
from analysis.storegraph import extendedtypes

from . import cpacontext

import itertools

HZ = 'HZ'
DN = 'DN'
UP = 'UP'
GLBL = 'GLBL'

class ConstraintNode(object):
	__slots__ = 'context', 'name', 'ci', 'values', 'diff', 'dirty', 'callbacks', 'typeSplit', 'exactSplit'
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

		self.typeSplit  = None
		self.exactSplit = None

	def attachTypeSplit(self, callback):
		if self.typeSplit is None:
			self.typeSplit = TypeSplitConstraint(self.context, self)
		self.typeSplit.addSplitCallback(callback)

	def getFiltered(self, typeFilter):
		return self.typeSplit.objects[typeFilter]

	def attachExactSplit(self, callback):
		if self.exactSplit is None:
			self.exactSplit = ExactSplitConstraint(self.context, self)
		self.exactSplit.addSplitCallback(callback)

	def markParam(self):
		pass

	def markReturn(self):
		pass

	def addCallback(self, callback):
		self.callbacks.append(callback)

	def markDirty(self):
		if not self.dirty:
			self.dirty = True
			self.context.dirtySlot(self)

	def updateValues(self, values):
		sm = self.context.analysis.setmanager
		# Not retained, so set manager is not used
		diff = sm.tempDiff(values, self.values)

		if diff:
			for value in diff:
				assert isinstance(value, AnalysisObject), value

			if self.callbacks:
				self.diff = sm.inplaceUnion(self.diff, diff)
				self.markDirty()
			else:
				assert not self.diff
				self.values = sm.inplaceUnion(self.values, diff)
			return True
		else:
			return False

	def updateSingleValue(self, value):
		assert isinstance(value, AnalysisObject), value
		if value not in self.values and value not in self.diff:
			sm = self.context.analysis.setmanager
			if self.callbacks:
				self.diff = sm.inplaceUnion(self.diff, [value])
				self.markDirty()
			else:
				assert not self.diff
				self.values = sm.inplaceUnion(self.values, [value])
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
		return "ao(%r, %s/%d)" % (self.name, self.qualifier, id(self))

	def cpaType(self):
		return self.name.cpaType()

class Constraint(object):
	__slots__ = ()
	def __init__(self):
		pass


class CopyConstraint(Constraint):
	__slots__ = 'src', 'dst'
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
		return "[%r -> %r]" % (self.src, self.dst)

class DownwardConstraint(Constraint):
	__slots__ = 'invoke', 'src', 'dst'
	def __init__(self, invoke, src, dst):
		assert isinstance(src, ConstraintNode), src
		assert isinstance(dst, ConstraintNode), dst
		Constraint.__init__(self)
		self.invoke = invoke
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
		for obj in diff:
			self.dst.updateSingleValue(self.invoke.copyDown(obj))

	def __repr__(self):
		return "[DN %r -> %r]" % (self.src, self.dst)


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
		slot = self.context.field(obj, self.fieldtype, field.name.obj)
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

		self.attach()
		self.makeConsistent()

	def attach(self):
		self.src.addCallback(self.srcChanged)
		self.field.addCallback(self.fieldChanged)

	def makeConsistent(self):
		# Make constraint consistent
		if self.src.values and self.field.values:
			self.srcChanged(self.src.values)


	def srcChanged(self, diff):
		pass

	def fieldChanged(self, diff):
		# TODO field is src
		pass

	def __repr__(self):
		return "[%s %r.%r CHECK=> %r]" % (self.fieldtype, self.src, self.field, self.dst)


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
		pass

	def fieldChanged(self, diff):
		# TODO field is dst
		pass

	def __repr__(self):
		return "[%s %r -> %r.%r]" % (self.fieldtype, self.src, self.dst, self.field)


class Splitter(Constraint):
	def addSplitCallback(self, callback):
		self.callbacks.append(callback)
		if self.objects: callback()

	def attach(self):
		self.src.addCallback(self.srcChanged)

	def makeConsistent(self):
		# Make constraint consistent
		if self.src.values:
			self.srcChanged(self.src.values)

	def doNotify(self):
		for callback in self.callbacks:
			callback()

class TypeSplitConstraint(Splitter):
	def __init__(self, context, src):
		assert isinstance(src, ConstraintNode), src
		self.context = context
		self.src = src
		self.objects = {}

		self.callbacks = []

		self.megamorphic = False

		self.attach()
		self.makeConsistent()

	def types(self):
		return self.objects.keys()

	def makeTempLocal(self):
		return self.context.local(ast.Local('type_split_temp'))

	def makeMegamorphic(self):
		assert not self.megamorphic
		self.megamorphic = True
		self.objects.clear()
		self.objects[cpacontext.anyType] = self.src
		self.doNotify()

	def srcChanged(self, diff):
		if self.megamorphic: return

		changed = False
		for obj in diff:
			cpaType = obj.cpaType()

			if cpaType not in self.objects:
				if len(self.objects) >= 4:
					self.makeMegamorphic()
					break
				else:
					temp = self.makeTempLocal()
					self.objects[cpaType] = temp
					changed = True
			else:
				temp = self.objects[cpaType]

			temp.updateSingleValue(obj)
		else:
			if changed: self.doNotify()




class ExactSplitConstraint(Splitter):
	def __init__(self, context, src):
		assert isinstance(src, ConstraintNode), src
		self.context = context
		self.src = src
		self.objects = {}
		self.callbacks = []

		self.attach()
		self.makeConsistent()

	def makeTempLocal(self):
		return self.context.local(ast.Local('exact_split_temp'))

	def srcChanged(self, diff):
		changed = False
		for obj in diff:
			if obj not in self.objects:
				temp = self.makeTempLocal()
				self.objects[obj] = temp
				changed = True
			else:
				temp = self.objects[obj]

			temp.updateSingleValue(obj)

		if changed: self.doNotify()
