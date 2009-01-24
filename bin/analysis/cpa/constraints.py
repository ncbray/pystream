import itertools
import base

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


class CachedConstraint(Constraint):
	__slots__ = 'cache'
	def __init__(self):
		Constraint.__init__(self)
		self.cache = set()

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
		CachedConstraint.__init__(self)
		self.op       = op
		self.expr     = expr
		self.slottype = slottype
		self.key      = key
		self.target   = target

	def update(self, sys):
		exprs = sys.read(self.expr)
		keys = sys.read(self.key)

		for args in itertools.product(exprs, keys):
			if not args in self.cache:
				self.cache.add(args)
			self.concreteUpdate(sys, *args)

	def concreteUpdate(self, sys, expr, key):
		slot = sys.canonical.objectSlot(expr, self.slottype, key.obj)
		if self.target:
			sys.createAssign(slot, self.target)
		sys.contextReads.add((self.expr.context, slot))
		sys.opReads[self.op].add(slot)

	def attach(self, sys):
		sys.constraint(self)
		sys.dependsRead(self, self.expr)
		sys.dependsRead(self, self.key)


class StoreConstraint(CachedConstraint):
	__slots__ = 'op', 'expr', 'slottype', 'key', 'value'
	def __init__(self, op, expr, slottype, key, value):
		CachedConstraint.__init__(self)
		self.op       = op
		self.expr     = expr
		self.slottype = slottype
		self.key      = key
		self.value    = value

	def update(self, sys):
		exprs = sys.read(self.expr)
		keys = sys.read(self.key)

		for args in itertools.product(exprs, keys):
			if not args in self.cache:
				self.cache.add(args)
				self.concreteUpdate(sys, *args)

	def concreteUpdate(self, sys, expr, key):
		slot = sys.canonical.objectSlot(expr, self.slottype, key.obj)
		sys.createAssign(self.value, slot)
		sys.contextModifies.add((self.expr.context, slot))
		sys.opModifies[self.op].add(slot)

	def attach(self, sys):
		sys.constraint(self)
		sys.dependsRead(self, self.expr)
		sys.dependsRead(self, self.key)


class AllocateConstraint(CachedConstraint):
	__slots__ = 'op', 'path', 'type_', 'target'
	def __init__(self, op, path, type_, target):
		CachedConstraint.__init__(self)
		self.op     = op
		self.path   = path
		self.type_  = type_
		self.target = target

	def update(self, sys):
		types = sys.read(self.type_)

		for type_ in types:
			if not type_ in self.cache:
				self.cache.add(type_)
				self.concreteUpdate(sys, type_)

	def concreteUpdate(self, sys, type_):
		if type_.obj.isType():
			sys.extractor.ensureLoaded(type_.obj)
			inst = type_.obj.abstractInstance()
			contextInst = sys.allocatedObject(self.path, inst)

			# Return the allocated object.
			sys.update(self.target, (contextInst,))

			#sys.allocation(self.op, self.type_.context, contextInst)
			sys.allocation(self.op.op, self.op.context, contextInst)

	def attach(self, sys):
		sys.constraint(self)
		sys.dependsRead(self, self.type_)
		sys.dependsWrite(self, self.target)

# Resolves the type of the expression, varg, and karg
class AbstractCallConstraint(CachedConstraint):
	__slots__ = 'op', 'path', 'selfarg', 'args', 'kwds', 'vargs', 'kargs', 'target'
	def __init__(self, op, path, selfarg, args, kwds, vargs, kargs, target):
		CachedConstraint.__init__(self)

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

	def update(self, sys):
		selfargs = sys.read(self.selfarg) if self.selfarg else (None,)
		vargs = sys.read(self.vargs) if self.vargs else (None,)
		kargs = sys.read(self.kargs) if self.kargs else (None,)

		for selfarg, varg, karg in itertools.product(selfargs, vargs, kargs):
			self.concreteUpdate(sys, selfarg, varg, karg)

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


		allslots = list(self.args)
		for i in range(vlength):
			index = sys.extractor.getObject(i)
			vslot = sys.canonical.objectSlot(vargs, 'Array', sys.existingObject(index).obj)
			allslots.append(vslot)

		division = len(code.parameters)
		argslots =  allslots[:division]
		vargslots = allslots[division:]

		con = SimpleCallConstraint(self.op, self.path, code, expr, allslots, argslots, vargslots, self.target)
		con.attach(sys)


	def attach(self, sys):
		sys.constraint(self)

		# To figure out the calling convention,
		# we must resolve the types of the expression, vargs, and kargs.

		# Note "not" works, "is not None" does not, as vargs and kargs may be empty containers.
		if not self.selfarg and not self.vargs and not self.kargs:
			# Nothing to resolve, so execute imediately
			self.mark(sys)
		else:
			if self.selfarg: sys.dependsRead(self, self.selfarg)
			if self.vargs: sys.dependsRead(self, self.vargs)
			if self.kargs: sys.dependsRead(self, self.kargs)



class CallConstraint(AbstractCallConstraint):
	__slots__ = ()
	def getCode(self, sys, selfType):
		return sys.extractor.getCall(selfType.obj).code

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
	__slots__ = 'op', 'path', 'code', 'selftype', 'slots', 'argslots', 'vargslots', 'target'

	def __init__(self, op, path, code, selftype, slots, argslots, vargslots, target):
		assert isinstance(op, base.OpContext), type(op)
		assert isinstance(code, ast.Code), type(code)
		assert target is None or isinstance(target, base.AbstractSlot), type(target)
		CachedConstraint.__init__(self)

		assert selftype is None or isinstance(selftype, base.ContextObject), selftype

		self.op   = op
		self.path = path
		self.code = code
		self.selftype = selftype

		# These slots are from the caller
		# These are slots are grouped according to their position in the callee.
		self.slots     = slots
		self.argslots  = argslots
		self.vargslots = vargslots

		self.target = target

	def update(self, sys):
		for args in itertools.product(*[sys.read(arg) for arg in self.slots]):
			self.concreteUpdate(sys, args)

	def concreteUpdate(self, sys, args):
		numParams = len(self.code.parameters)
		targetcontext = sys.canonicalContext(self.code, self.path, self.selftype, args[:numParams], args[numParams:])

		if targetcontext not in self.cache:
			self.cache.add(targetcontext)

			sys.bindCall(self.op, targetcontext, self.target)

			# Only used for lifetime analysis?
			sys.opInvokes[self.op].add(targetcontext)

	def attach(self, sys):
		sys.constraint(self)

		if self.slots:
			for arg in self.slots:
				sys.dependsRead(self, arg)
		else:
			# If there's no arguments, the constraint should start dirty.
			self.mark(sys)



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
