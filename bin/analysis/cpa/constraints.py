import itertools
from analysis.storegraph import storegraph
from analysis.storegraph import canonicalobjects
from analysis.storegraph import extendedtypes

import language.python.calling

# HACK to testing if a object is a bool True/False...
from language.python import ast, program

import util.tvl

import analysis.cpasignature

class Constraint(object):
	__slots__ = 'sys', 'dirty'

	def __init__(self, sys):
		self.dirty = False
		self.sys = sys
		self.attach()

	def process(self):
		assert self.dirty
		self.dirty = False
		self.update()

	def update(self):
		raise NotImplementedError

	def mark(self):
		if not self.dirty:
			self.dirty = True
			self.sys.dirty.append(self)

	def getBad(self):
		return [slot for slot in self.reads() if slot is not None and not slot.refs]

	def check(self, console):
		bad = self.getBad()

		if bad:
			console.output("Unresolved %r:" % self.name())
			for slot in bad:
				console.output("\t%r" % slot)
			console.output('')

class CachedConstraint(Constraint):
	__slots__ = 'observing', 'cache'
	def __init__(self, sys, *args):
		self.observing = args
		self.cache = set()

		Constraint.__init__(self, sys)

	def update(self):
		values = [(None,) if slot is None else slot.refs for slot in self.observing]

		for args in itertools.product(*values):
			if not args in self.cache:
				self.cache.add(args)
			self.concreteUpdate(*args)

	def attach(self):
		self.sys.constraint(self)

		depends = False
		for slot in self.observing:
			if slot is not None:
				slot.dependsRead(self)
				depends = True

		if not depends:
			# Nothing will trigger this constraint...
			self.mark()

	def name(self):
		return self.op.op

	def reads(self):
		return self.observing

	def writes(self):
		return (self.target,)

class AssignmentConstraint(Constraint):
	__slots__ = 'sourceslot', 'destslot'
	def __init__(self, sys, sourceslot, destslot):
		assert isinstance(sourceslot, storegraph.SlotNode), sourceslot
		assert isinstance(destslot, storegraph.SlotNode), destslot

		self.sourceslot = sourceslot
		self.destslot   = destslot

		Constraint.__init__(self, sys)


	def update(self):
		self.destslot = self.destslot.update(self.sourceslot)

	def attach(self):
		self.sys.constraint(self)
		self.sourceslot.dependsRead(self)
		self.destslot.dependsWrite(self)

	def name(self):
		return self

	def reads(self):
		return (self.sourceslot,)

	def writes(self):
		return (self.destslot,)


class LoadConstraint(CachedConstraint):
	__slots__ = 'op', 'expr', 'slottype', 'key', 'target'
	def __init__(self, sys, op, expr, slottype, key, target):
		assert isinstance(expr, storegraph.SlotNode), type(expr)
		assert isinstance(key,  storegraph.SlotNode), type(key)

		self.op       = op
		self.expr     = expr
		self.slottype = slottype
		self.key      = key
		self.target   = target

		CachedConstraint.__init__(self, sys, expr, key)

	def concreteUpdate(self, exprType, keyType):
		assert keyType.isExisting() or keyType.isExternal(), keyType

		obj   = self.expr.region.object(exprType)
		name  = self.sys.canonical.fieldName(self.slottype, keyType.obj)

		if self.target:
			field = obj.field(name, self.target.region)
			self.sys.createAssign(field, self.target)
		else:
			# The load is being discarded.  This is probally in a
			# descriptive stub.  As such, we want to log the read.
			field = obj.field(name, self.expr.region.group.regionHint)

		self.sys.logRead(self.op, field)


class StoreConstraint(CachedConstraint):
	__slots__ = 'op', 'expr', 'slottype', 'key', 'value'
	def __init__(self, sys, op, expr, slottype, key, value):
		self.op       = op
		self.expr     = expr
		self.slottype = slottype
		self.key      = key
		self.value    = value

		CachedConstraint.__init__(self, sys, expr, key)

	def concreteUpdate(self, exprType, keyType):
		assert keyType.isExisting() or keyType.isExternal(), keyType

		obj   = self.expr.region.object(exprType)
		name  = self.sys.canonical.fieldName(self.slottype, keyType.obj)
		field = obj.field(name, self.value.region)

		self.sys.createAssign(self.value, field)
		self.sys.logModify(self.op, field)

	def writes(self):
		return ()

class AllocateConstraint(CachedConstraint):
	__slots__ = 'op', 'type_', 'target'
	def __init__(self, sys, op, type_, target):
		self.op     = op
		self.type_  = type_
		self.target = target

		CachedConstraint.__init__(self, sys, type_)

	def concreteUpdate(self, type_):
		if type_.obj.isType():
			xtype = self.sys.extendedInstanceType(self.op.context, type_, id(self.op.op))
			obj = self.target.initializeType(xtype)
			self.sys.logAllocation(self.op, obj)

	def attach(self):
		CachedConstraint.attach(self)
		self.target.dependsWrite(self)


class CheckConstraint(CachedConstraint):
	__slots__ = 'op', 'expr', 'slottype', 'key', 'target'
	def __init__(self, sys, op, expr, slottype, key, target):
		assert isinstance(expr, storegraph.SlotNode), type(expr)
		assert isinstance(key,  storegraph.SlotNode), type(key)
		assert target

		self.op       = op
		self.expr     = expr
		self.slottype = slottype
		self.key      = key
		self.target   = target

		CachedConstraint.__init__(self, sys, expr, key)

	def concreteUpdate(self, exprType, keyType):
		assert keyType.isExisting() or keyType.isExternal(), keyType

		self.expr = self.expr.getForward()

		obj   = self.expr.region.object(exprType)
		name  = self.sys.canonical.fieldName(self.slottype, keyType.obj)

		slot = obj.field(name, obj.region.group.regionHint)

		con = SimpleCheckConstraint(self.sys, self.op, slot, self.target)

		# Constraints are usually not marked based on an existing null...
		if slot.null: con.mark()

class SimpleCheckConstraint(Constraint):
	__slots__ = 'op', 'slot', 'target', 'refs', 'null'
	def __init__(self, sys, op, slot, target):
		self.op       = op
		self.slot     = slot
		self.target   = target

		self.refs     = False
		self.null     = False

		Constraint.__init__(self, sys)

	def emit(self, pyobj):
		obj   = self.sys.extractor.getObject(pyobj)
		xtype = self.sys.canonical.existingType(obj)

		# HACK initalize type implies then reference is never null...
		# Make sound?
		cobj = self.target.initializeType(xtype)
		assert cobj is not None
		self.sys.logAllocation(self.op, cobj)


	def update(self):
		if not self.refs and self.slot.refs:
			self.sys.logRead(self.op, self.slot)
			self.emit(True)
			self.refs = True

		if not self.null and self.slot.null:
			self.sys.logRead(self.op, self.slot)
			self.emit(False)
			self.null = True

	def attach(self):
		self.sys.constraint(self)
		self.slot.dependsRead(self)
		self.target.dependsWrite(self)

	def name(self):
		return self.op.op

	def reads(self):
		# Reads no locals.
		return ()

	def write(self):
		return (self.target,)


# Resolves the type of the expression, varg, and karg
class AbstractCallConstraint(CachedConstraint):
	__slots__ = 'op', 'selfarg', 'args', 'kwds', 'vargs', 'kargs', 'targets'
	def __init__(self, sys, op, selfarg, args, kwds, vargs, kargs, targets):
		assert isinstance(op, canonicalobjects.OpContext), type(op)
		assert isinstance(args, (list, tuple)), args
		assert not kwds, kwds
		assert targets is None or isinstance(targets, (list, tuple)), type(targets)

		self.op      = op
		self.selfarg = selfarg
		self.args    = args
		self.kwds    = kwds
		self.vargs   = vargs
		self.kargs   = kargs

		self.targets  = targets

		CachedConstraint.__init__(self, sys, selfarg, vargs, kargs)


	def getVArgLengths(self, vargsType):
		if vargsType is not None:
			assert isinstance(vargsType, extendedtypes.ExtendedType), type(vargsType)
			vargsObj = self.vargs.region.object(vargsType)
			slotName = self.sys.storeGraph.lengthSlotName
			field    = vargsObj.field(slotName, None)
			self.sys.logRead(self.op, field)

			lengths = []
			for lengthType in field.refs:
				assert lengthType.isExisting()
				lengths.append(lengthType.obj.pyobj)

			return lengths
		else:
			return (0,)


	def concreteUpdate(self, expr, vargs, kargs):
		for vlength in self.getVArgLengths(vargs):
			key = (expr, vargs, kargs, vlength)
			if not key in self.cache:
				self.cache.add(key)
				self.finalCombination(expr, vargs, kargs, vlength)

	def finalCombination(self, expr, vargs, kargs, vlength):
		code = self.getCode(expr)

		assert code, "Attempted to call uncallable object:\n%r\n\nat op:\n%r\n\nwith args:\n%r\n\n" % (expr.obj, self.op, vargs)

		callee = code.codeParameters()
		numArgs = len(self.args)+vlength
		info = language.python.calling.callStackToParamsInfo(callee, expr is not None, numArgs, False, None, False)

		if info.willSucceed.maybeTrue():
			allslots = list(self.args)

			if vargs:
				vargsObj = self.vargs.region.object(vargs)
				for index in range(vlength):
					slotName = self.sys.canonical.fieldName('Array', self.sys.extractor.getObject(index))
					field = vargsObj.field(slotName, None)
					allslots.append(field)
					self.sys.logRead(self.op, field)


			# HACK this is actually somewhere between caller and callee...
			caller = language.python.calling.CallerArgs(self.selfarg, allslots, [], None, None, self.targets)

			SimpleCallConstraint(self.sys, self.op, code, expr, allslots, caller)

	def writes(self):
		if self.targets:
			return self.targets
		else:
			return ()


class CallConstraint(AbstractCallConstraint):
	__slots__ = ()
	def getCode(self, selfType):
		code = self.sys.getCall(selfType.obj)
		if code is None:
			return self.sys.extractor.stubs.exports['interpreter_call']
		else:
			return code

#TODO If there's no selfv, vargs, or kargs, turn into a simple call?
class DirectCallConstraint(AbstractCallConstraint):
	__slots__ = ('code',)

	def __init__(self, sys, op, code, selfarg, args, kwds, vargs, kargs, target):
		assert code.isCode(), type(code)
		self.code = code

		AbstractCallConstraint.__init__(self, sys, op, selfarg, args, kwds, vargs, kargs, target)

	def getCode(self, selfType):
		return self.code


# Resolves argument types, given and exact function, self type,
# and list of argument slots.
# TODO make contextual?
class SimpleCallConstraint(CachedConstraint):
	__slots__ = 'op', 'code', 'selftype', 'slots', 'caller', 'megamorphic'

	def __init__(self, sys, op, code, selftype, slots, caller):
		assert isinstance(op, canonicalobjects.OpContext), type(op)
		assert code.isCode(), type(code)
		assert selftype is None or isinstance(selftype, extendedtypes.ExtendedType), selftype

		self.op       = op
		self.code     = code
		self.selftype = selftype
		self.slots    = slots
		self.caller   = caller

		self.megamorphic = [False for s in slots]

		CachedConstraint.__init__(self, sys, *slots)

	def concreteUpdate(self, *argsTypes):
		targetcontext = self.sys.canonicalContext(self.op, self.code, self.selftype, argsTypes)
		self.sys.bindCall(self.op, self.caller, targetcontext)

	def clearInvocations(self):
		# TODO eliminate constraints if target invocation is unused?
		self.cache.clear()
		self.sys.opInvokes[self.op].clear()

	def processMegamorphic(self, values):
		numValues = len(values)
		limit = 4 if len(values) < 3 else 3

		# Look for new megamorphic arguments
		changed = False
		for i, value in enumerate(values):
			if not self.megamorphic[i]:
				if len(value) > limit:
					self.megamorphic[i] = True
					changed = True

			if self.megamorphic[i]:
				values[i] = (analysis.cpasignature.Any,)
		return changed

	def update(self):
		values = [(None,) if slot is None else slot.refs for slot in self.observing]

		changed = self.processMegamorphic(values)

		if changed: self.clearInvocations()

		for args in itertools.product(*values):
			if not args in self.cache:
				self.cache.add(args)
			self.concreteUpdate(*args)

	def writes(self):
		if self.caller.returnargs:
			return self.caller.returnargs
		else:
			return ()

class DeferedSwitchConstraint(Constraint):
	def __init__(self, sys, extractor, cond, t, f):
		self.extractor = extractor
		self.cond = cond
		self.t = t
		self.f = f

		self.tDefered = True
		self.fDefered = True

		Constraint.__init__(self, sys)

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

	def update(self):
		if self.tDefered or self.fDefered:
			for condType in self.cond.refs:
				self.updateBranching(self.getBranch(condType))

	def attach(self):
		self.sys.constraint(self)
		self.cond.dependsRead(self)

	def name(self):
		return "if %r" % self.cond

	def reads(self):
		return (self.cond,)

	def writes(self):
		return ()


class DeferedTypeSwitchConstraint(Constraint):
	def __init__(self, sys, op, extractor, cond, cases):
		self.op = op
		self.extractor = extractor
		self.cond = cond

		self.cases       = cases
		self.switchSlots = [extractor.localSlot(case.expr) for case in cases]

		self.caseLUT    = {}
		self.deferedLUT = {}
		for case in cases:
			for t in case.types:
				self.caseLUT[t.object] = case
			self.deferedLUT[case] = True

		self.cache = set()

		Constraint.__init__(self, sys)

	def update(self):
		for ref in self.cond.refs:
			# Only process a given xtype once.
			if ref in self.cache: continue
			self.cache.add(ref)

			# Log that the type field has been read.
			region   =  self.sys.storeGraph.regionHint
			refObj   = region.object(ref)
			slotName = self.sys.storeGraph.typeSlotName
			field    = refObj.field(slotName, region)
			self.sys.logRead(self.op, field)

			# Setup
			t = ref.obj.type
			case = self.caseLUT[t]
			slot = self.extractor.localSlot(case.expr)

			# Transfer the (filtered) reference
			# HACK this may poison regions?
			slot.initializeType(ref)

			# If the case has not be extracted yet, do it.
			if self.deferedLUT[case]:
				self.deferedLUT[case] = False
				self.extractor(case.body)

	def attach(self):
		self.sys.constraint(self)
		self.cond.dependsRead(self)
		for slot in self.switchSlots:
			slot.dependsWrite(self)

	def name(self):
		return "type switch %r" % self.cond

	def reads(self):
		return (self.cond,)

	def writes(self):
		return self.switchSlots