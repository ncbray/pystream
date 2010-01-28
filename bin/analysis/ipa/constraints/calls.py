import itertools
from .. calling import cpa, transfer, callbinder
from . import node

class AbstractCall(object):
	def __init__(self):
		self.dirty = False
		self.cache = {}

def argIsOK(arg):
	return arg is None or isinstance(arg, node.ConstraintNode)

nullObjects = {None:None}

class UserCallConstraint(AbstractCall):
	def __init__(self, context, op, selfarg, args, kwds, varg, karg, targets):
		AbstractCall.__init__(self)
		self.context = context
		self.op = op
		self.selfarg = selfarg
		self.args = args
		self.kwds = kwds
		self.varg = varg
		self.karg = karg
		self.targets = targets

		assert self.selfarg or self.varg

		if self.selfarg:
			self.selfarg.attachExactSplit(self.splitChanged)

		if self.varg:
			self.varg.attachExactSplit(self.splitChanged)

	def splitChanged(self):
		if not self.dirty:
			self.dirty = True
			self.context.dirtyCall(self)

	def __repr__(self):
		return "[CALL %r(%r, %r, *%r, **%r) -> %r]" % (self.selfarg, self.args, self.kwds, self.varg, self.karg, self.targets)

	def selfObjects(self):
		if self.selfarg:
			return self.selfarg.exactSplit.objects
		else:
			return nullObjects

	def vargObjects(self):
		if self.varg:
			return self.varg.exactSplit.objects
		else:
			return nullObjects


	def tupleSlots(self, tupleObj):
		slots = []

		if tupleObj is None: return slots

		assert tupleObj.obj().pythonType() is tuple, tupleObj

		analysis = self.context.analysis

		lengthSlot = self.context.field(tupleObj, 'LowLevel', analysis.pyObj('length'))
		assert len(lengthSlot.values) == 1, tupleObj
		length = tuple(lengthSlot.values)[0].pyObj()


		for i in range(length):
			slot = self.context.field(tupleObj, 'Array', analysis.pyObj(i))
			slots.append(slot)

		return slots

	def defaultSlots(self, selfObj):
		if selfObj is None: return []

		# Relies on func_defaults being immutable.

		defaultsSlot = self.context.field(selfObj, 'Attribute', self.context.analysis.funcDefaultName)
		if defaultsSlot.null:
			assert len(defaultsSlot.values) == 0
			return []

		assert len(defaultsSlot.values) == 1

		defaultsObj = tuple(defaultsSlot.values)[0]

		pt = defaultsObj.obj().pythonType()
		if pt is type(None):
			return []
		elif pt is tuple:
			return self.tupleSlots(defaultsObj)
		else:
			assert False, "func_defaults is a %r?" % pt

	def resolve(self, context):
		self.dirty = False

		for (selfobj, selflcl), (vargobj, varglcl) in itertools.product(self.selfObjects().iteritems(), self.vargObjects().iteritems()):
			key = (selfobj, vargobj)
			if key not in self.cache:
				self.cache[key] = None

				code = self.getCode(context, selfobj)

				vargSlots    = self.tupleSlots(vargobj)
				defaultSlots = self.defaultSlots(selfobj)

				context.fcall(self.op, code, selflcl, self.args, vargSlots, defaultSlots, self.targets)

class CallConstraint(UserCallConstraint):
	def getCode(self, context, selfobj):
			return context.analysis.getCode(selfobj)


class DirectCallConstraint(UserCallConstraint):
	def __init__(self, context, op, code, selfarg, args, kwds, varg, karg, targets):
		UserCallConstraint.__init__(self, context, op, selfarg, args, kwds, varg, karg, targets)
		self.code = code

	def getCode(self, context, selfobj):
			return self.code


class ConcreteCallConstraint(AbstractCall):
	def __init__(self, context, op, code, selfarg, args, kwds, varg, karg, targets, vargSlots, defaultSlots):
		assert code is not None
		assert argIsOK(selfarg), selfarg
		AbstractCall.__init__(self)
		self.context = context
		self.op = op
		self.code = code
		self.selfarg = selfarg
		self.args = args
		self.kwds = kwds
		self.varg = varg
		self.karg = karg
		self.targets = targets

		# TODO no need for the split locals?
		self.varg.attachExactSplit(self.splitChanged)

	def splitChanged(self):
		if not self.dirty:
			self.dirty = True
			self.context.dirtyDCall(self)

	def __repr__(self):
		return "[DCALL %s %r(%r, %r, *%r, **%r) -> %r]" % (self.code, self.selfarg, self.args, self.kwds, self.varg, self.karg, self.targets)

	def vargObjSlots(self, vargObj):
		slots = []

		if vargObj is None: return slots

		analysis = self.context.analysis

		lengthSlot = self.context.field(vargObj, 'LowLevel', analysis.pyObj('length'))
		assert len(lengthSlot.values) == 1
		length = tuple(lengthSlot.values)[0].pyObj()


		for i in range(length):
			slot = self.context.field(vargObj, 'Array', analysis.pyObj(i))
			slots.append(slot)

		return slots

	def resolve(self, context):
		self.dirty = False

		assert self.varg

		for vargObj in self.varg.exactSplit.objects.iterkeys():
			key = vargObj
			if key not in self.cache:
				self.cache[key] = None

				vargSlots = self.vargObjSlots(vargObj)
				context.fcall(self.op, self.code, self.selfarg, self.args, self.kwds, vargSlots, self.karg, self.targets)


class FlatCallConstraint(AbstractCall):
	def __init__(self, context, op, code, selfarg, args, vargSlots, defaultSlots, targets):
		assert argIsOK(selfarg), selfarg

		AbstractCall.__init__(self)
		self.context = context
		self.op = op
		self.code = code
		self.selfarg = selfarg
		self.args = args
		self.vargSlots = vargSlots
		self.defaultSlots = defaultSlots
		self.targets = targets

		returnarglen = len(self.targets) if self.targets is not None else 0
		self.info = transfer.computeTransferInfo(self.code, self.selfarg is not None, len(self.args), len(self.vargSlots), len(self.defaultSlots), returnarglen)

		if self.info.maybeOK():
			if self.selfarg is not None:
				self.selfarg.attachTypeSplit(self.splitChanged)

			for arg in args:
				arg.attachTypeSplit(self.splitChanged)

			for arg in vargSlots:
				arg.attachTypeSplit(self.splitChanged)

			for arg in defaultSlots:
				arg.attachTypeSplit(self.splitChanged)
		else:
			import pdb
			pdb.set_trace()

	def splitChanged(self):
		if not self.dirty:
			self.dirty = True
			self.context.dirtyFCall(self)

	def __repr__(self):
		return "[FCALL %s %r(%r, %r, *%r, **%r) -> %r]" % (self.code, self.selfarg, self.args, self.kwds, self.varg, self.karg, self.targets)

	def resolve(self, context):
		self.dirty = False

		info = self.info
		ctsb = cpa.CPATypeSigBuilder(context.analysis, self, info)
		info.transfer(ctsb, ctsb)
		sigs = ctsb.signatures()

		for sig in sigs:
			if not sig in self.cache:
				print sig

				# HACK - varg can be weird, must take it into account?
				self.cache[sig] = None

				invokedC = context.analysis.getContext(sig)
				invoke = callbinder.bind(self, invokedC, info)

				# TODO is this a good idea?
				invoke.apply()
