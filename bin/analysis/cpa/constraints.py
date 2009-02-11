import itertools
from . import base
from . import storegraph
from . import extendedtypes

# HACK to testing if a object is a bool True/False...
from programIR.python import ast, program

import util.tvl

class Constraint(object):
	__slots__ = 'dirty', 'path'

	def __init__(self):
		self.dirty = False

	def process(self, sys):
		assert self.dirty
		self.dirty = False
		self.update(sys)

	def update(self, sys):
		raise NotImplementedError

	def mark(self, sys):
		if not self.dirty:
			self.dirty = True
			sys.dirty.append(self)

	def check(self, console):
		pass

class CachedConstraint(Constraint):
	__slots__ = 'observing', 'cache'
	def __init__(self, *args):
		Constraint.__init__(self)
		self.observing = args
		self.cache = set()

	def update(self, sys):
		values = [(None,) if slot is None else slot.refs for slot in self.observing]

		for args in itertools.product(*values):
			if not args in self.cache:
				self.cache.add(args)
			self.concreteUpdate(sys, *args)

	def attach(self, sys):
		sys.constraint(self)

		depends = False
		for slot in self.observing:
			if slot is not None:
				slot.dependsRead(sys, self)
				depends = True

		if not depends:
			# Nothing will trigger this constraint...
			self.mark(sys)

	def check(self, console):
		bad = []
		for slot in self.observing:
			if slot is not None and not slot.refs:
				bad.append(slot)

		if bad:
			console.output("Unresolved %r:" % self.op.op)
			for slot in bad:
				console.output("\t%r" % slot)


class AssignmentConstraint(Constraint):
	__slots__ = 'sourceslot', 'destslot'
	def __init__(self, sourceslot, destslot):
		assert isinstance(sourceslot, storegraph.SlotNode), sourceslot
		assert isinstance(destslot, storegraph.SlotNode), destslot

		Constraint.__init__(self)
		self.sourceslot = sourceslot
		self.destslot   = destslot

	def update(self, sys):
		self.destslot.update(sys, self.sourceslot)

	def attach(self, sys):
		sys.constraint(self)
		self.sourceslot.dependsRead(sys, self)
		self.destslot.dependsWrite(sys, self)

class LoadConstraint(CachedConstraint):
	__slots__ = 'op', 'expr', 'slottype', 'key', 'target'
	def __init__(self, op, expr, slottype, key, target):
		assert isinstance(expr, storegraph.SlotNode), type(expr)
		assert isinstance(key,  storegraph.SlotNode), type(key)

		CachedConstraint.__init__(self, expr, key)
		self.op       = op
		self.expr     = expr
		self.slottype = slottype
		self.key      = key
		self.target   = target

	def concreteUpdate(self, sys, exprType, keyType):
		assert keyType.isExisting() or keyType.isExternal(), keyType

		obj   = self.expr.region.object(sys, exprType)
		name  = sys.canonical.fieldName(self.slottype, keyType.obj)

		if self.target:
			field = obj.field(sys, name, self.target.region)
			sys.createAssign(field, self.target)
		else:
			# The load is being discarded.  This is probally in a
			# descriptive stub.  As such, we want to log the read.
			field = obj.field(sys, name, self.expr.region.group.regionHint)

		sys.logRead(self.op, field)



class StoreConstraint(CachedConstraint):
	__slots__ = 'op', 'expr', 'slottype', 'key', 'value'
	def __init__(self, op, expr, slottype, key, value):
		CachedConstraint.__init__(self, expr, key)
		self.op       = op
		self.expr     = expr
		self.slottype = slottype
		self.key      = key
		self.value    = value

	def concreteUpdate(self, sys, exprType, keyType):
		assert keyType.isExisting() or keyType.isExternal(), keyType

		obj   = self.expr.region.object(sys, exprType)
		name  = sys.canonical.fieldName(self.slottype, keyType.obj)
		field = obj.field(sys, name, self.value.region)

		sys.createAssign(self.value, field)
		sys.logModify(self.op, field)


class AllocateConstraint(CachedConstraint):
	__slots__ = 'op', 'type_', 'target'
	def __init__(self, op, type_, target):
		CachedConstraint.__init__(self, type_)
		self.op     = op
		self.type_  = type_
		self.target = target

	def concreteUpdate(self, sys, type_):
		if type_.obj.isType():
			xtype = sys.extendedInstanceType(self.op.context, type_)
			obj = self.target.initializeType(sys, xtype)
			sys.logAllocation(self.op, obj)

	def attach(self, sys):
		CachedConstraint.attach(self, sys)
		self.target.dependsWrite(sys, self)


class CheckConstraint(CachedConstraint):
	__slots__ = 'op', 'expr', 'slottype', 'key', 'target'
	def __init__(self, op, expr, slottype, key, target):
		assert isinstance(expr, storegraph.SlotNode), type(expr)
		assert isinstance(key,  storegraph.SlotNode), type(key)
		assert target

		CachedConstraint.__init__(self, expr, key)
		self.op       = op
		self.expr     = expr
		self.slottype = slottype
		self.key      = key
		self.target   = target

	def concreteUpdate(self, sys, exprType, keyType):
		assert keyType.isExisting() or keyType.isExternal(), keyType

		self.expr = self.expr.getForward()

		obj   = self.expr.region.object(sys, exprType)
		name  = sys.canonical.fieldName(self.slottype, keyType.obj)

		slot = obj.field(sys, name, obj.region.group.regionHint)

		con = SimpleCheckConstraint(self.op, slot, self.target)
		con.attach(sys)

		# Constraints are usually not marked based on an existing null...
		if slot.null: con.mark(sys)

class SimpleCheckConstraint(Constraint):
	__slots__ = 'op', 'slot', 'target', 'refs', 'null'
	def __init__(self, op, slot, target):
		Constraint.__init__(self)
		self.op       = op
		self.slot     = slot
		self.target   = target

		self.refs     = False
		self.null     = False

	def emit(self, sys, pyobj):
		obj = sys.extractor.getObject(pyobj)
		xtype = sys.canonical.existingType(obj)

		# HACK initalize type implies then reference is never null...
		# Make sound?
		self.target.initializeType(sys, xtype)

	def update(self, sys):
		if not self.refs and self.slot.refs:
			self.emit(sys, True)
			self.refs = True

		if not self.null and self.slot.null:
			self.emit(sys, False)
			self.null = True

	def attach(self, sys):
		sys.constraint(self)
		self.slot.dependsRead(sys, self)
		self.target.dependsWrite(sys, self)

# Resolves the type of the expression, varg, and karg
class AbstractCallConstraint(CachedConstraint):
	__slots__ = 'op', 'selfarg', 'args', 'kwds', 'vargs', 'kargs', 'target'
	def __init__(self, op, selfarg, args, kwds, vargs, kargs, target):
		CachedConstraint.__init__(self, selfarg, vargs, kargs)

		assert isinstance(args, (list, tuple)), args
		assert not kwds, kwds
		assert target is None or isinstance(target, storegraph.SlotNode), type(target)

		self.op      = op
		self.selfarg = selfarg
		self.args    = args
		self.kwds    = kwds
		self.vargs   = vargs
		self.kargs   = kargs

		self.target  = target

	def getVArgLengths(self, sys, vargsType):
		if vargsType is not None:
			assert isinstance(vargsType, extendedtypes.ExtendedType), type(vargsType)
			vargsObj = self.vargs.region.object(sys, vargsType)
			slotName = sys.lengthSlotName
			field    = vargsObj.field(sys, slotName, None)

			lengths = []
			for lengthType in field.refs:
				assert lengthType.isExisting()
				lengths.append(lengthType.obj.pyobj)

			return lengths
		else:
			return (0,)


	def concreteUpdate(self, sys, expr, vargs, kargs):
		for vlength in self.getVArgLengths(sys, vargs):
			key = (expr, vargs, kargs, vlength)
			if not key in self.cache:
				self.cache.add(key)
				self.finalCombination(sys, expr, vargs, kargs, vlength)

	def finalCombination(self, sys, expr, vargs, kargs, vlength):
		code = self.getCode(sys, expr)

		assert code, "Attempted to call uncallable object:\n%r\n\nat op:\n%r\n\nwith args:\n%r\n\n" % (expr.obj, self.op, vargs)

		callee = util.calling.CalleeParams.fromCode(code)
		numArgs = len(self.args)+vlength
		info = util.calling.callStackToParamsInfo(callee, expr is not None, numArgs, False, None, False)

		if info.willSucceed.maybeTrue():
			allslots = list(self.args)

			if vargs:
				vargsObj = self.vargs.region.object(sys, vargs)
				for index in range(vlength):
					slotName = sys.canonical.fieldName('Array', sys.extractor.getObject(index))
					field = vargsObj.field(sys, slotName, None)
					allslots.append(field)

			# HACK this is actually somewhere between caller and callee...
			caller = util.calling.CallerArgs(self.selfarg, allslots, [], None, None, self.target)

			con = SimpleCallConstraint(self.op, code, expr, allslots, caller)
			con.attach(sys)


class CallConstraint(AbstractCallConstraint):
	__slots__ = ()
	def getCode(self, sys, selfType):
		return sys.getCall(selfType.obj)

#TODO If there's no selfv, vargs, or kargs, turn into a simple call?
class DirectCallConstraint(AbstractCallConstraint):
	__slots__ = ('code',)

	def __init__(self, op, code, selfarg, args, kwds, vargs, kargs, target):
		assert isinstance(code, ast.Code), type(code)
		AbstractCallConstraint.__init__(self, op, selfarg, args, kwds, vargs, kargs, target)
		self.code = code

	def getCode(self, sys, selfType):
		return self.code


# Resolves argument types, given and exact function, self type,
# and list of argument slots.
# TODO make contextual?
class SimpleCallConstraint(CachedConstraint):
	__slots__ = 'op', 'code', 'selftype', 'slots', 'caller'

	def __init__(self, op, code, selftype, slots, caller):
		assert isinstance(op, base.OpContext), type(op)
		assert isinstance(code, ast.Code), type(code)
		assert selftype is None or isinstance(selftype, extendedtypes.ExtendedType), selftype
		CachedConstraint.__init__(self, *slots)

		self.op       = op
		self.code     = code
		self.selftype = selftype
		self.slots    = slots
		self.caller   = caller

	def concreteUpdate(self, sys, *argsTypes):
		targetcontext = sys.canonicalContext(self.op, self.code, self.selftype, argsTypes)
		sys.bindCall(self.op, self.caller, targetcontext)


class DeferedSwitchConstraint(Constraint):
	def __init__(self, extractor, cond, t, f):
		Constraint.__init__(self)

		self.extractor = extractor
		self.cond = cond
		self.t = t
		self.f = f

		self.tDefered = True
		self.fDefered = True

	def getBranch(self, cobj):
		obj = cobj.obj
		if isinstance(obj, program.Object) and isinstance(obj.pyobj, (bool, int, long, float, str)):
			return util.tvl.tvl(obj.pyobj)
		else:
			return util.tvl.TVLMaybe

	def updateBranching(self, branch):
		# Process defered branches, if they will be taken.
		if branch.maybeTrue() and self.tDefered:
			self.tDefered = False
			self.extractor(self.t)

		if branch.maybeFalse() and self.fDefered:
			self.fDefered = False
			self.extractor(self.f)

	def update(self, sys):
		if self.tDefered or self.fDefered:
			for condType in self.cond.refs:
				self.updateBranching(self.getBranch(condType))

	def attach(self, sys):
		sys.constraint(self)
		self.cond.dependsRead(sys, self)
