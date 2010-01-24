from language.python import ast # Debugging
from . import split
from .. calling import cpa
from .. model import objectname

class ConstraintNode(object):
	__slots__ = 'context', 'name', 'ci', 'values', 'diff', 'null', 'dirty', 'callbacks', 'typeSplit', 'exactSplit'
	def __init__(self, context, name, ci=False):
		assert not isinstance(name, ast.DoNotCare), name

		self.context = context
		self.name = name
		self.ci = ci

		self.values = context.analysis.setmanager.empty()
		self.diff   = context.analysis.setmanager.empty()

		self.null = False

		self.dirty = False

		self.callbacks = []

		self.typeSplit  = None
		self.exactSplit = None

	def attachTypeSplit(self, callback):
		if self.typeSplit is None:
			self.typeSplit = split.TypeSplitConstraint(self.context, self)
			self.context.constraint(self.typeSplit)
		self.typeSplit.addSplitCallback(callback)

	def getFiltered(self, typeFilter):
		if typeFilter is cpa.anyType:
			return self
		else:
			return self.typeSplit.objects[typeFilter]

	def attachExactSplit(self, callback):
		if self.exactSplit is None:
			self.exactSplit = split.ExactSplitConstraint(self.context, self)
			self.context.constraint(self.exactSplit)
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
				assert value.isObjectName(), value

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
		assert value.isObjectName(), value
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

	def markNull(self):
		if not self.null:
			self.null = True
			if self.callbacks:
				# HACK this is an expensive way of communicating with the
				# few consumers that care.  Fortunately, this is rare.
				self.markDirty()

	def clearNull(self):
		# Can only be done before the node is observed.
		assert not self.callbacks
		self.null = False

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
			callback(self.context, diff)

	def __repr__(self):
		return "slot(%r/%d)" % (self.name, id(self))

	def isNode(self):
		return True
