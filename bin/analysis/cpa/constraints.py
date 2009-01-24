import itertools
import base

# HACK to testing if a object is a bool True/False...
from programIR.python import ast, program

import util.tvl

# For allocation
from util import xtypes

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


class CachedConstraint(Constraint):
	__slots__ = 'observing', 'cache'
	def __init__(self, *args):
		Constraint.__init__(self)
		self.observing = args
		self.cache = set()

	def update(self, sys):
		values = [sys.read(slot) for slot in self.observing]

		for args in itertools.product(*values):
			if not args in self.cache:
				self.cache.add(args)
			self.concreteUpdate(sys, *args)

	def attach(self, sys):
		sys.constraint(self)

		depends = False
		for slot in self.observing:
			if slot is not None:
				sys.dependsRead(self, slot)
				depends = True

		if not depends:
			# Nothing will trigger this constraint...
			self.mark(sys)


class AssignmentConstraint(Constraint):
	__slots__ = 'sourceslot', 'destslot'
	def __init__(self, sourceslot, destslot):
		assert isinstance(sourceslot, base.AbstractSlot), sourceslot
		assert isinstance(destslot, base.AbstractSlot), destslot

		Constraint.__init__(self)
		self.sourceslot = sourceslot
		self.destslot   = destslot

	def update(self, sys):
		values = sys.read(self.sourceslot)
		sys.update(self.destslot, values)

	def attach(self, sys):
		sys.constraint(self)
		sys.dependsRead(self, self.sourceslot)
		sys.dependsWrite(self, self.destslot)


class LoadConstraint(CachedConstraint):
	__slots__ = 'op', 'expr', 'slottype', 'key', 'target'
	def __init__(self, op, expr, slottype, key, target):
		CachedConstraint.__init__(self, expr, key)
		self.op       = op
		self.expr     = expr
		self.slottype = slottype
		self.key      = key
		self.target   = target

	def concreteUpdate(self, sys, expr, key):
		slot = sys.canonical.objectSlot(expr, self.slottype, key.obj)
		sys.logRead(self.op, slot)
		if self.target: sys.createAssign(slot, self.target)


class StoreConstraint(CachedConstraint):
	__slots__ = 'op', 'expr', 'slottype', 'key', 'value'
	def __init__(self, op, expr, slottype, key, value):
		CachedConstraint.__init__(self, expr, key)
		self.op       = op
		self.expr     = expr
		self.slottype = slottype
		self.key      = key
		self.value    = value

	def concreteUpdate(self, sys, expr, key):
		slot = sys.canonical.objectSlot(expr, self.slottype, key.obj)
		sys.logModify(self.op, slot)
		sys.createAssign(self.value, slot)


class AllocateConstraint(CachedConstraint):
	__slots__ = 'op', 'path', 'type_', 'target'
	def __init__(self, op, path, type_, target):
		CachedConstraint.__init__(self, type_)
		self.op     = op
		self.path   = path
		self.type_  = type_
		self.target = target

	def extendedType(self, sys, type_):
		context = sys.canonical.pathContext(self.path)

		pyobj = type_.obj.pyobj
		if pyobj is xtypes.MethodType:
			sig = self.op.context.signature
			# TODO check that this is "new"?
			if len(sig.params) == 1 and len(sig.vparams) == 3:
				func = sig.vparams[0]
				inst = sig.vparams[1]
				context = sys.canonical.methodContext(func, inst)

		sys.ensureLoaded(type_.obj)
		instObj = type_.obj.abstractInstance()
		contextInst = sys.allocatedObject(context, instObj)
		return contextInst


	def concreteUpdate(self, sys, type_):
		if type_.obj.isType():
			contextInst = self.extendedType(sys, type_)
			sys.logAllocation(self.op, contextInst)

			# Return the allocated object.
			sys.update(self.target, (contextInst,))


	def attach(self, sys):
		CachedConstraint.attach(self, sys)
		sys.dependsWrite(self, self.target)


# Resolves the type of the expression, varg, and karg
class AbstractCallConstraint(CachedConstraint):
	__slots__ = 'op', 'path', 'selfarg', 'args', 'kwds', 'vargs', 'kargs', 'target'
	def __init__(self, op, path, selfarg, args, kwds, vargs, kargs, target):
		CachedConstraint.__init__(self, selfarg, vargs, kargs)

		assert isinstance(args, (list, tuple)), args
		assert not kwds, kwds
		assert target is None or isinstance(target, base.AbstractSlot), type(target)

		self.op      = op
		self.path    = path
		self.selfarg = selfarg
		self.args    = args
		self.kwds    = kwds
		self.vargs   = vargs
		self.kargs   = kargs

		self.target  = target

	def getVArgLengths(self, sys, vargs):
		if vargs is not None:
			lengthStr  = sys.extractor.getObject('length')
			lengthSlot = sys.canonical.objectSlot(vargs, 'LowLevel', sys.existingObject(lengthStr).obj)

			lengths = []

			for vlengthObj in sys.read(lengthSlot):
				vlength = vlengthObj.obj.pyobj
				assert isinstance(vlength, int), vlength
				lengths.append(vlength)

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
			for i in range(vlength):
				index = sys.extractor.getObject(i)
				vslot = sys.canonical.objectSlot(vargs, 'Array', sys.existingObject(index).obj)
				allslots.append(vslot)

			con = SimpleCallConstraint(self.op, self.path, code, expr, allslots, self.target)
			con.attach(sys)


class CallConstraint(AbstractCallConstraint):
	__slots__ = ()
	def getCode(self, sys, selfType):
		return sys.getCall(selfType.obj)

#TODO If there's no selfv, vargs, or kargs, turn into a simple call?
class DirectCallConstraint(AbstractCallConstraint):
	__slots__ = ('code',)

	def __init__(self, op, path, code, selfarg, args, kwds, vargs, kargs, target):
		assert isinstance(code, ast.Code), type(code)
		AbstractCallConstraint.__init__(self, op, path, selfarg, args, kwds, vargs, kargs, target)
		self.code = code

	def getCode(self, sys, selfType):
		return self.code


# Resolves argument types, given and exact function, self type,
# and list of argument slots.
# TODO make contextual?
class SimpleCallConstraint(CachedConstraint):
	__slots__ = 'op', 'path', 'code', 'selftype', 'slots', 'target'

	def __init__(self, op, path, code, selftype, slots, target):
		assert isinstance(op, base.OpContext), type(op)
		assert isinstance(code, ast.Code), type(code)
		assert selftype is None or isinstance(selftype, base.ContextObject), selftype
		assert target is None or isinstance(target, base.AbstractSlot), type(target)
		CachedConstraint.__init__(self, *slots)

		self.op       = op
		self.path     = path
		self.code     = code
		self.selftype = selftype
		self.slots    = slots
		self.target   = target

	def concreteUpdate(self, sys, *args):
		numParams = len(self.code.parameters)
		targetcontext = sys.canonicalContext(self.code, self.path, self.selftype, args[:numParams], args[numParams:])
		sys.bindCall(self.op, targetcontext, self.target)


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
			for cond in sys.read(self.cond):
				self.updateBranching(self.getBranch(cond))

	def attach(self, sys):
		sys.constraint(self)
		sys.dependsRead(self, self.cond)
