from . import cpacontext
from . import transfer
from . import constraints

from language.python import ast

class AbstractCall(object):
	def __init__(self):
		self.cache = {}

class CallConstraint(AbstractCall):
	def __init__(self, selfarg, args, kwds, varg, karg, targets):
		AbstractCall.__init__(self)
		self.selfarg = selfarg
		self.args = args
		self.kwds = kwds
		self.varg = varg
		self.karg = karg
		self.targets = targets

	def __repr__(self):
		return "[CALL %r(%r, %r, *%r, **%r) -> %r]" % (self.selfarg, self.args, self.kwds, self.varg, self.karg, self.targets)

	def resolve(self, context):
		for co in self.selfarg.objs:
			if co not in self.cache:
				print "selfarg???", co
				code = context.analysis.getCode(co)
				context.dcall(code, co, self.args, self.kwds, self.varg, self.karg, self.targets)

				self.cache[co] = None

class DirectCallConstraint(AbstractCall):
	def __init__(self, code, selfarg, args, kwds, varg, karg, targets):
		assert code is not None
		AbstractCall.__init__(self)
		self.code = code
		self.selfarg = selfarg
		self.args = args
		self.kwds = kwds
		self.varg = varg
		self.karg = karg
		self.targets = targets

	def __repr__(self):
		return "[DCALL %s %r(%r, %r, *%r, **%r) -> %r]" % (self.code, self.selfarg, self.args, self.kwds, self.varg, self.karg, self.targets)

	def groupedVArgs(self, context):
		groups = {}

		lengthName = context.analysis.lengthName()

		for on in self.varg.objs:
			obj = on
			values = context.load((obj, lengthName))

			for valueObj in values:
				value = valueObj.name.obj.pyobj
				if value not in groups:
					groups[value] = [obj]
				else:
					groups[value].append(obj)

		return groups


	def resolve(self, context):
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
		assert isinstance(varg, int), varg
		AbstractCall.__init__(self)
		self.code = code
		self.selfarg = selfarg
		self.args = args
		self.kwds = kwds
		self.varg = varg
		self.karg = karg
		self.targets = targets

		self.vargObjs = set()

#		self.vargFiltered = context.local(ast.Local('varg_%d' % varg))

		self.vargTemp = []
		for i in range(varg):
			lc = context.local(ast.Local('varg_%d_%d'%(varg,i)))
			self.vargTemp.append(lc)

#			index = context.analysis.pyObj(i)
#			il = context.local(ast.Local('index_%d' % i))
#			context.assign(index, il)
#
#			context.constraint(constraints.LoadConstraint(self.vargFiltered, 'Array', il, lc))

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
			fieldName = context.analysis.canonical.fieldName('Array', index.name.obj)
			slot = (obj, fieldName)
			context.constraint(constraints.ConcreteLoadConstraint(slot, ac))


	def __repr__(self):
		return "[DCALL %s %r(%r, %r, *%r, **%r) -> %r]" % (self.code, self.selfarg, self.args, self.kwds, self.varg, self.karg, self.targets)


	def resolve(self, context):
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

					invoked = context.analysis.getContext(sig)
					context.analysis.bindCall(self, invoked, info)

					# HACK - varg can be wierd, must take it into account?
					self.cache[sig] = None
		else:
			import pdb
			pdb.set_trace()
