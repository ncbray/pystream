from . import cpacontext
from . import transfer
from . import constraints

from language.python import ast

class AbstractCall(object):
	def __init__(self):
		self.dirty = False
		self.cache = {}

def argIsOK(arg):
	return arg is None or isinstance(arg, constraints.ConstraintNode)

class CallConstraint(AbstractCall):
	def __init__(self, context, selfarg, args, kwds, varg, karg, targets):
		AbstractCall.__init__(self)
		self.context = context
		self.selfarg = selfarg
		self.args = args
		self.kwds = kwds
		self.varg = varg
		self.karg = karg
		self.targets = targets

		self.selfarg.addCallback(self.argChanged)

		self.argChanged(None)

	def argChanged(self, diff):
		if not self.dirty:
			self.dirty = True
			self.context.dirtyCall(self)

	def __repr__(self):
		return "[CALL %r(%r, %r, *%r, **%r) -> %r]" % (self.selfarg, self.args, self.kwds, self.varg, self.karg, self.targets)

	def resolve(self, context):
		self.dirty = False

		for obj in self.selfarg.values:
			key = obj.name
			if key not in self.cache:
				#print "selfarg???", key

				lcl = context.local(ast.Local('call_expr'), (obj,)) # HACK?
				self.cache[key] = lcl

				code = context.analysis.getCode(obj)
				context.dcall(code, lcl, self.args, self.kwds, self.varg, self.karg, self.targets)

			else:
				self.cache[key].updateValues(frozenset([obj]))

class DirectCallConstraint(AbstractCall):
	def __init__(self, context, code, selfarg, args, kwds, varg, karg, targets):
		assert code is not None
		assert argIsOK(selfarg), selfarg
		AbstractCall.__init__(self)
		self.context = context
		self.code = code
		self.selfarg = selfarg
		self.args = args
		self.kwds = kwds
		self.varg = varg
		self.karg = karg
		self.targets = targets

		self.varg.addCallback(self.argChanged)

		self.argChanged(None)


	def argChanged(self, diff):
		if not self.dirty:
			self.dirty = True
			self.context.dirtyDCall(self)

	def __repr__(self):
		return "[DCALL %s %r(%r, %r, *%r, **%r) -> %r]" % (self.code, self.selfarg, self.args, self.kwds, self.varg, self.karg, self.targets)

	def groupedVArgs(self, context):
		groups = {}

		lengthName = context.analysis.compiler.extractor.getObject('length')

		for obj in self.varg.values:
			# HACK should be monitoring this slot?
			lengthSlot = context.field(obj, 'LowLevel', lengthName)
			values = lengthSlot.values

			for valueObj in values:
				value = valueObj.name.obj.pyobj
				if value not in groups:
					groups[value] = [obj]
				else:
					groups[value].append(obj)

		return groups


	def resolve(self, context):
		self.dirty = False

		assert self.varg
		group = self.groupedVArgs(context)

		for count, objs in group.iteritems():
			if count not in self.cache:
				call = context.fcall(self.code, self.selfarg, self.args, self.kwds, count, self.karg, self.targets)
				self.cache[count] = call
			else:
				call = self.cache[count]
			call.updateVArgObjs(context, objs)


class FlatCallConstraint(AbstractCall):
	def __init__(self, context, code, selfarg, args, kwds, varg, karg, targets):
		assert argIsOK(selfarg), selfarg
		assert isinstance(varg, int), varg

		AbstractCall.__init__(self)
		self.context = context
		self.code = code
		self.selfarg = selfarg
		self.args = args
		self.kwds = kwds
		self.varg = varg
		self.karg = karg
		self.targets = targets

		self.vargObjs = set()

		for arg in args:
			arg.addCallback(self.argChanged)

		self.vargTemp = []
		for i in range(varg):
			lc = context.local(ast.Local('varg_%d_%d'%(varg,i)))
			self.vargTemp.append(lc)

			lc.addCallback(self.argChanged)

		self.argChanged(None)

	def argChanged(self, diff):
		if not self.dirty:
			self.dirty = True
			self.context.dirtyFCall(self)

	# TODO directly generate the loads?
	def updateVArgObjs(self, context, objs):
		assert self.varg
		for obj in objs:
			if obj not in self.vargObjs:
				self.vargObjs.add(obj)
				self.transferVObj(context, obj)

	def transferVObj(self, context, obj):
		for i, ac in enumerate(self.vargTemp):
			index = context.analysis.pyObj(i)
			slot = context.field(obj, 'Array', index.name.obj)
			context.assign(slot, ac)

	def __repr__(self):
		return "[FCALL %s %r(%r, %r, *%r, **%r) -> %r]" % (self.code, self.selfarg, self.args, self.kwds, self.varg, self.karg, self.targets)


	def resolve(self, context):
		self.dirty = False

		assert not self.kwds
		assert self.karg is None

		info = transfer.computeTransferInfo(self.code, self.selfarg is not None, len(self.args), self.varg)

		if info.maybeOK():
			ctsb = cpacontext.CPATypeSigBuilder(context.analysis, self, info)
			info.transfer(ctsb, ctsb)
			sigs = ctsb.signatures()

			for sig in sigs:
				if not sig in self.cache:
					print sig

					# HACK - varg can be weird, must take it into account?
					self.cache[sig] = None

					invoked = context.analysis.getContext(sig)
					context.analysis.bindCall(self, invoked, info)

		else:
			import pdb
			pdb.set_trace()
