from util import explodeCombonations
#from base import LocalSlot

# HACK
from programIR.python import program

import base

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

	def clean(self):
		assert self.dirty
		self.dirty = True

	def mark(self, sys):
		if not self.dirty:
			self.dirty = True
			sys.dirty.append(self)


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
		sys.dependsRead(self, self.sourceslot)


class LoadConstraint(Constraint):
	__slots__ = 'op', 'expr', 'slottype', 'key', 'target', 'cache'
	def __init__(self, op, expr, slottype, key, target):
		Constraint.__init__(self)
		self.op       = op
		self.expr     = expr
		self.slottype = slottype
		self.key      = key
		self.target   = target

		self.cache = set()

	def update(self, sys):
		exprs = sys.read(self.expr)
		keys = sys.read(self.key)
		
		explodeCombonations(self.concreteCombination, 0, (sys,), exprs, keys)

	def concreteCombination(self, sys, expr, key):
		slot = sys.canonical.objectSlot(expr, self.slottype, key.obj)
		
		if not slot in self.cache:
			self.cache.add(slot)

			sys.createAssign(slot, self.target)
			sys.contextReads.add((self.expr.context, slot))
			sys.opReads[self.op].add(slot)

	def attach(self, sys):
		sys.dependsRead(self, self.expr)
		sys.dependsRead(self, self.key)



class StoreConstraint(Constraint):
	__slots__ = 'op', 'expr', 'slottype', 'key', 'value', 'cache'
	def __init__(self, op, expr, slottype, key, value):
		Constraint.__init__(self)
		self.op       = op
		self.expr     = expr
		self.slottype = slottype
		self.key      = key
		self.value    = value

		self.cache = set()

	def update(self, sys):
		exprs = sys.read(self.expr)
		keys = sys.read(self.key)
		explodeCombonations(self.concreteCombination, 0, (sys,), exprs, keys)

	def concreteCombination(self, sys, expr, key):
		slot = sys.canonical.objectSlot(expr, self.slottype, key.obj)
		
		if not slot in self.cache:
			self.cache.add(slot)

			sys.createAssign(self.value, slot)
			sys.contextModifies.add((self.expr.context, slot))
			sys.opModifies[self.op].add(slot)



	def attach(self, sys):
		sys.dependsRead(self, self.expr)
		sys.dependsRead(self, self.key)


class AllocateConstraint(Constraint):
	__slots__ = 'op', 'path', 'type_', 'target', 'allocated'
	def __init__(self, op, path, type_, target):
		Constraint.__init__(self)
		self.op     = op
		self.path   = path
		self.type_  = type_
		self.target = target

		self.allocated = set()
		
	def update(self, sys):
		types = sys.read(self.type_)
		for type_ in types:
			if not type_ in self.allocated:
				self.allocated.add(type_)

				if type_.obj.isType():
					sys.extractor.ensureLoaded(type_.obj)
					inst = type_.obj.abstractInstance()
					contextInst = sys.allocatedObject(self.path, inst)
					
					# Return the allocated object.
					sys.update(self.target, (contextInst,))

					sys.allocations.add((self.type_.context, contextInst))
					sys.opAllocates[self.op].add(contextInst)

	def attach(self, sys):
		sys.dependsRead(self, self.type_)


# Resolves the type of the expression, varg, and karg
class AbstractCallConstraint(Constraint):
	__slots__ = 'op', 'path', 'selfarg', 'args', 'kwds', 'vargs', 'kargs', 'target', 'calls'
	def __init__(self, op, path, selfarg, args, kwds, vargs, kargs, target):
		Constraint.__init__(self)

		assert isinstance(args, (list, tuple)), args
		assert not kwds, kwds

		self.op      = op
		self.path    = path
		self.selfarg = selfarg
		self.args    = args
		self.kwds    = kwds
		self.vargs   = vargs
		self.kargs   = kargs
		
		self.target  = target

		self.calls = set()

	def update(self, sys):
		selfarg = sys.read(self.selfarg) if self.selfarg else (None,)
		vargs = sys.read(self.vargs) if self.vargs else (None,)
		kargs = sys.read(self.kargs) if self.kargs else (None,)
		explodeCombonations(self.concreteCombination, 0, (sys,), selfarg, vargs, kargs)

	def concreteCombination(self, sys, expr, vargs, kargs):
		if vargs is not None:
			lengthStr = sys.extractor.getObject('length')
			lengthSlot = sys.canonical.objectSlot(vargs, 'LowLevel', sys.existingObject(lengthStr).obj)

			for vlengthObj in sys.read(lengthSlot):
				vlength = vlengthObj.obj.pyobj
				assert isinstance(vlength, int), vlength
				self.finalCombination(sys, expr, vargs, kargs, vlength)
		else:
			self.finalCombination(sys, expr, vargs, kargs, 0)

	def finalCombination(self, sys, expr, vargs, kargs, vlength):
		key = (expr, vargs, kargs, vlength)

		if not key in self.calls:
			self.calls.add(key)

			func = self.getFunc(sys, expr)

			if func:
				allslots = list(self.args)
				for i in range(vlength):
					index = sys.extractor.getObject(i)
					vslot = sys.canonical.objectSlot(vargs, 'Array', sys.existingObject(index).obj)
					allslots.append(vslot)

				division = len(func.code.parameters)
				argslots =  allslots[:division]
				vargslots = allslots[division:]
				
				con = SimpleCallConstraint(self.op, self.path, func, expr, allslots, argslots, vargslots, self.target)
				con.attach(sys)			
			else:
				assert func, "Attempted to call uncallable object:\n%r\n\nat op:\n%r\n\nwith args:\n%r\n\n" % (expr.obj, self.op, vargs)


	def attach(self, sys):
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
	def getFunc(self, sys, selfType):
		return sys.extractor.getCall(selfType.obj)
	
#TODO If there's no selfv, vargs, or kargs, turn into a simple call?
class DirectCallConstraint(AbstractCallConstraint):
	__slots__ = ('func',)

	def __init__(self, op, path, func, selfarg, args, kwds, vargs, kargs, target):
		AbstractCallConstraint.__init__(self, op, path, selfarg, args, kwds, vargs, kargs, target)
		self.func = func

	def getFunc(self, sys, selfType):
		return self.func



# Resolves argument types, given and exact function, self type,
# and list of argument slots.

class SimpleCallConstraint(Constraint):
	__slots__ = 'op', 'path', 'func', 'selftype', 'slots', 'argslots', 'vargslots', 'target', 'invocations'
	
	def __init__(self, op, path, func, selftype, slots, argslots, vargslots, target):
		assert selftype is None or isinstance(selftype, base.ContextObject), selftype

		Constraint.__init__(self)

		self.op   = op
		self.path = path
		self.func = func
		self.selftype = selftype

		# These slots are from the caller
		# These are slots are grouped according to their position in the callee.
		self.slots     = slots
		self.argslots  = argslots
		self.vargslots = vargslots
				
		self.target = target

		self.invocations = set()

	def update(self, sys):
		# TODO use util.calling to generate args
		args = [sys.read(arg) for arg in self.slots]
		explodeCombonations(self.concreteCombination, 0, (sys,), *args)

	def concreteCombination(self, sys, *args):
		numParams = len(self.func.code.parameters)
		params  = args[:numParams]
		vparams = args[numParams:]
		
		targetcontext = sys.canonicalContext(self.path, self.func, self.selftype, params, vparams)
		
		if not targetcontext in self.invocations:
			self.invocations.add(targetcontext)
			
			sys.bindCall(self.target, targetcontext)

			# Only used for lifetime analysis?
			sys.opInvokes[self.op].add(targetcontext)

	def attach(self, sys):
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

	def update(self, sys):
		if self.tDefered or self.fDefered:
			# Figure if either branch is taken.
			tLive, fLive = False, False
			
			cond = sys.read(self.cond)
			for cobj in cond:
				obj = cobj.obj
				if isinstance(obj, program.Object) and isinstance(obj.pyobj, (bool, int, long, float, str)):
					if obj.pyobj:
						tLive = True
					else:
						fLive = True
				else:
					tLive, fLive =  True, True

			# Process defered branches, if they're taken.
			if tLive and self.tDefered:
				self.tDefered = False
				self.extractor(self.t)

			if fLive and self.fDefered:
				self.fDefered = False
				self.extractor(self.f)


	def attach(self, sys):
		sys.dependsRead(self, self.cond)
