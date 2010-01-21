from language.python import ast
from analysis.storegraph import extendedtypes

import itertools

HZ = 'HZ'
DN = 'DN'
UP = 'UP'
GLBL = 'GLBL'

class ConstraintNode(object):
	def isLocal(self):
		return False

	def isObject(self):
		return False

class LocalNode(ConstraintNode):
	def __init__(self, name, ci=False):
		assert isinstance(name, ast.Local), name
		self.name = name
		self.ci = ci

		self.prevObj = []

		self.objs = set()

		# Fact, does not flow
		self.param   = False
		self.ret     = False

		# Flows forward
		self.holding = False
		self.holdingEsc = False

		# Flows backward
		self.prop    = False
		self.propRet = False

		# Forward flow depends on backward flow


	def markParam(self):
		if not self.param:
			self.param = True
			self.markHolding()

	def markReturn(self):
		if not self.ret:
			self.ret = True
			self.markPropReturn()

	def markHolding(self):
		if not self.holding:
			self.holding = True

	def markHoldingEsc(self):
		if not self.holdingEsc:
			self.holdingEsc = True

	def markProp(self):
		if not self.prop:
			self.prop = True

	def markPropReturn(self):
		if not self.propRet:
			self.propRet = True

	def isLocal(self):
		return True

	def __repr__(self):
		return "%r" % self.name


	def assignmentSource(self, c):
		other = c.dst
		if self.isObject():
			if self.opaque: other.markHoldingEsc()
		else:
			if self.holding: other.markHolding()

	def assignmentDestination(self, c):
		other = c.src
		if other.isObject():
			if self.prop or self.propRet: other.markOpaque()
		else:
			if self.prop: other.markProp()
			if self.propRet: other.markPropReturn()


class ObjectNode(ConstraintNode):
	def __init__(self, name, ci=False):
		assert isinstance(name, extendedtypes.ExtendedType), name
		self.name = name
		self.ci   = ci

		# Flows forward
		self.opaque  = False

		# HACK?
		self.objs = set([self])

	def markOpaque(self):
		if not self.opaque:
			self.opaque = True

	def isObject(self):
		return True

	def __repr__(self):
		return "%r" % self.name


	def assignmentSource(self, c):
		other = c.dst
		if self.isObject():
			if self.opaque: other.markHoldingEsc()
		else:
			if self.holding: other.markHolding()

	def assignmentDestination(self, c):
		other = c.src
		if other.isObject():
			if self.prop or self.propRet: other.markOpaque()
		else:
			if self.prop: other.markProp()
			if self.propRet: other.markPropReturn()

class Constraint(object):
	__slots__ = 'qualifier'

class ObjectConstraint(Constraint):
	def __init__(self, obj, dst):
		self.obj = obj
		self.dst = dst

		if obj.ci:
			self.qualifier = GLBL
		else:
			self.qualifier = HZ

	def __repr__(self):
		return "[%s %r -> %r]" % (self.qualifier, self.obj, self.dst)

	def resolve(self, context):
		self.dst.objs.add(self.obj)
		self.dst.prevObj.append(self)

# TODO object load and store constraints?

class CopyConstraint(Constraint):
	def __init__(self, src, dst):
		assert isinstance(src, LocalNode), src
		assert isinstance(dst, LocalNode), dst

		self.src = src
		self.dst = dst

	def __repr__(self):
		return "[%s %r -> %r]" % (self.qualifier, self.src, self.dst)

	def resolve(self, context):
		for oc in self.src.prevObj:
			context.deriveCopy(self, oc)

class FilteredCopyConstraint(Constraint):
	def __init__(self, src, filter, dst):
		assert isinstance(src, LocalNode), src
		assert isinstance(dst, LocalNode), dst

		self.src    = src
		self.filter = filter
		self.dst    = dst

	def __repr__(self):
		return "[%s %r %r -> %r]" % (self.qualifier, self.filter, self.src,  self.dst)

	def resolve(self, context):
		for oc in self.src.prevObj:
			if oc.obj is self.filter:
				context.deriveCopy(self, oc)

class LoadConstraint(Constraint):
	def __init__(self, src, fieldtype, field, dst):
		assert isinstance(src, LocalNode), src
		assert isinstance(fieldtype, str), fieldtype
		assert isinstance(field, LocalNode), field
		assert isinstance(dst, LocalNode), dst

		self.src   = src
		self.fieldtype = fieldtype
		self.field = field
		self.dst   = dst

		self.qualifier = HZ

	def __repr__(self):
		return "[%s %s %r.%r -> %r]" % (self.qualifier, self.fieldtype, self.src, self.field, self.dst)

	def resolve(self, context):
		for src, field in itertools.product(self.src.prevObj, self.field.prevObj):
			assert False

class StoreConstraint(Constraint):
	def __init__(self, src, dst, fieldtype, field):
		assert isinstance(src, LocalNode), src
		assert isinstance(dst, LocalNode), dst
		assert isinstance(fieldtype, str), fieldtype
		assert isinstance(field, LocalNode), field

		self.src   = src
		self.dst   = dst
		self.fieldtype = fieldtype
		self.field = field

		self.qualifier = HZ

	def __repr__(self):
		return "[%s %s %r -> %r.%r]" % (self.qualifier, self.fieldtype, self.src, self.dst, self.field)


class ConcreteStoreConstraint(Constraint):
	def __init__(self, src, slot):
		assert isinstance(src, LocalNode), src

		self.src   = src
		self.slot  = slot

		self.qualifier = HZ

	def __repr__(self):
		return "[%s %r -> %r]" % (self.qualifier, self.src, self.slot)

	def resolve(self, context):
		for oc in self.src.prevObj:
			context.store(oc.obj, self.slot)

class ConcreteLoadConstraint(Constraint):
	def __init__(self, slot, dst):
		assert isinstance(dst, LocalNode), dst

		self.slot  = slot
		self.dst   = dst

		self.qualifier = HZ

	def __repr__(self):
		return "[%s %r -> %r]" % (self.qualifier, self.slot, self.dst)

	def resolve(self, context):
		for oc in context.load(self.slot):
			context.assign(oc, self.dst)
