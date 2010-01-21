from .. cpa import simpleimagebuilder

from .constraintextractor import ConstraintExtractor

from . import constraints, calls


from language.python import ast

import itertools

# TODO only if decompiled?
from optimization.callconverter import callConverter


class CallBinder(object):
	def __init__(self, call, context):
		self.call    = call
		self.context = context

		self.params = self.context.signature.code.codeParameters()

	def getSelfArg(self):
		return self.call.selfarg

	def getArg(self, i):
		return self.call.args[i]

	def getVArg(self, i):
		return self.call.vargTemp[i]


	def setSelfParam(self, value):
		filter = self.context.signature.selfparam
		dst = self.context.local(self.params.selfparam)
		self.copyDownFiltered(value, filter, dst)

	def setParam(self, i, value):
		filter = self.context.signature.params[i]
		dst = self.context.local(self.params.params[i])
		self.copyDownFiltered(value, filter, dst)

	def setVParam(self, i, value):
		filter = self.context.signature.vparams[i]
		dst = self.context.vparamTemp[i]
		self.copyDownFiltered(value, filter, dst)


	def copyDownFiltered(self, src, filter, dst):
		if filter is not cpacontext.anyType:
			self.context.assignFiltered(src, filter, dst, constraints.DN)
		else:
			self.copyDown(src, dst)

	def copyDown(self, src, dst):
		self.context.assignFiltered(src, dst, constraints.DN)

# Context setup
# Allocate vparam/kparam
# store temp locals in vparam/kparams
class Context(object):
	def __init__(self, analysis, signature):
		self.analysis    = analysis
		self.signature   = signature
		self.constraints = []

		self.calls       = []
		self.dcalls      = []
		self.fcalls      = []

		self.locals      = {}

		self.memory = {}

		code = signature.code

		if code:
			params = code.codeParameters()
			hasVParam = params.vparam is not None

			if hasVParam:
				self.setupVParam(params.vparam)

	def setupVParam(self, vparam):
		numVParam = len(self.signature.vparams)

		inst = self.analysis.tupleInstance()
		xtype = self.analysis.canonical.contextType(self.signature, inst, None)
		vparamO = self.analysis.object(xtype)

		vparamC = self.local(vparam)

		self.assign(vparamO, vparamC)

		index = self.analysis.pyObj(numVParam)
		lengthName = self.analysis.lengthName()

		self.store(index, (vparamO, lengthName))

		self.vparamTemp = []
		for i in range(numVParam):
				lcl = ast.Local('vparam%d'%i)
				lc = self.local(lcl)
				self.vparamTemp.append(lc)

				index = self.analysis.pyObj(i)

				fieldName = self.analysis.canonical.fieldName('Array', index.name.obj)
				slot = (vparamO, fieldName)
				self.constraint(constraints.ConcreteStoreConstraint(lc, slot))

	def deriveCopy(self, copy, oc):
		c = constraints.ObjectConstraint(oc.obj, copy.dst)

		if copy.qualifier is constraints.DN:
			c.qualifier = constraints.DN
		elif oc.qualifier is constraints.GLBL:
			c.qualifer = constraints.GLBL
		elif copy.ci:
			c.qualifier = constraints.GLBL
		else:
			if copy.qualifier is constraints.HZ:
				c.qualifier = oc.qualifier
			elif copy.qualifier is constraints.GLBL:
				c.qualifier = constraints.GLBL
			elif copy.qualifier is constraints.UP:
					return # Do not derive!
			else:
				assert False, copy.qualifer

		self.constraint(c)



	def constraint(self, constraint):
		self.constraints.append(constraint)
		self.analysis._constraint(self, constraint)

	def call(self, selfarg, args, kwds, varg, karg, targets):
		self.calls.append(calls.CallConstraint(selfarg, args, kwds, varg, karg, targets))

	def dcall(self, code, selfarg, args, kwds, varg, karg, targets):
		if varg is None:
			self.fcall(code, selfarg, args, kwds, 0, karg, targets)
		else:
			call = calls.DirectCallConstraint(code, selfarg, args, kwds, varg, karg, targets)
			self.dcalls.append(call)

	def fcall(self, code, selfarg, args, kwds, varg, karg, targets):
		call = calls.FlatCallConstraint(self, code, selfarg, args, kwds, varg, karg, targets)
		self.fcalls.append(call)
		return call


	def local(self, node):
		if node not in self.locals:
			cnode = constraints.LocalNode(node)
			self.locals[node] = cnode
		else:
			cnode = self.locals[node]
		return cnode

	def assign(self, src, dst, qualifier=constraints.HZ):
		if src.isObject():
			constraint = constraints.ObjectConstraint(src, dst)
		else:
			constraint = constraints.CopyConstraint(src, dst)

		constraint.qualifier = qualifier
		self.constraint(constraint)

	def assignFiltered(self, src, filter, dst, qualifier=constraints.HZ):
		if src.isObject():
			if src.name is filter:
				constraint = constraints.ObjectConstraint(src, dst)
			else:
				return
		else:
			constraint = constraints.FilteredCopyConstraint(src, filter, dst)
		constraint.qualifier = qualifier
		self.constraint(constraint)


	### Store model ###
	def store(self, data, slot):
#		print 'store'
#		print data.name
#		print slot
#		print

		if slot not in self.memory:
			self.memory[slot] = set()
		self.memory[slot].add(data)

	def load(self, slot):
#		print 'load'
#		print slot, slot in self.memory
#		print

		return self.memory.get(slot, ())


	def dump(self):

		print self.signature
		print

		for lc in self.locals.itervalues():
			print lc
			print '\t', lc.objs
		print

		for slot, refs in self.memory.iteritems():
			print slot
			print '\t', refs

		print

class IPAnalysis(object):
	def __init__(self, compiler, canonical):
		self.compiler = compiler
		self.canonical = canonical

		self.objs = {}
		self.contexts = {}

		self.root = self.getContext(cpacontext.externalContext)

		self.constraints = []

		self.sigs = {}

		self.liveCode = set()

	def lengthName(self):
		lenO = self.compiler.extractor.getObject('length')
		return self.canonical.fieldName('LowLevel', lenO)


	def tupleInstance(self):
		tupleCls = self.compiler.extractor.getObject(tuple)
		self.compiler.extractor.ensureLoaded(tupleCls)
		return tupleCls.typeinfo.abstractInstance

	def _constraint(self, context, constraint):
		self.constraints.append((context, constraint))

	def canonicalSignature(self, sig):
		return self.sigs.setdefault(sig, sig)

	def pyObj(self, pyobj):
		obj = self.compiler.extractor.getObject(pyobj)
		xtype = self.canonical.existingType(obj)
		return self.object(xtype, True)

	def object(self, xtype, glbl=False):
		if xtype not in self.objs:
			cnode = constraints.ObjectNode(xtype, glbl)
			self.objs[xtype] = cnode
		else:
			cnode = self.objs[xtype]
		return cnode

	def makeFakeLocal(self, objs):
		if objs is None: return None

		lcl = ast.Local('entry_point_arg')
		cl = self.root.local(lcl)

		for obj in objs:
			co = self.object(obj, True)
			self.root.constraint(constraints.ObjectConstraint(co, cl))

		return cl

	def makeFakeEntryPointOp(self, ep, epargs):
		selfarg = self.makeFakeLocal(epargs.selfarg)

		args = []
		for arg in epargs.args:
			args.append(self.makeFakeLocal(arg))

		varg = self.makeFakeLocal(epargs.vargs)
		karg = self.makeFakeLocal(epargs.kargs)

		self.root.dcall(ep.code, selfarg, args, [], varg, karg, None)

	def getContext(self, sig):
		if sig not in self.contexts:
			context = Context(self, sig)
			self.contexts[sig] = context

			if sig.code:
				ce = ConstraintExtractor(self, context)
				ce.process()
		else:
			context = self.contexts[sig]
		return context

	def bindCall(self, call, context, info):
		print "BIND"
		binder = CallBinder(call, context)
		info.transfer(binder, binder)



	def getCode(self, co):
		obj = co.name.obj

		code = self.compiler.extractor.getCall(obj)
		if code is None:
			code = self.sys.extractor.stubs.exports['interpreter_call']

		if code not in self.liveCode:
			callConverter(self.compiler.extractor, code)
			self.liveCode.add(code)


		print "code", code

		return code

	def updateCallGraph(self):
		print "update"

		changed = False

		# HACK dictionary size may change...
		for context in tuple(self.contexts.itervalues()):
			for call in context.calls:
				call.resolve(context)

			for dcall in context.dcalls:
				dcall.resolve(context)

			for fcall in context.fcalls:
				fcall.resolve(context)


		print

		return len(self.constraints) > 0

	def resolveConstraints(self):
		print "resolve"
		while self.constraints:
			context, constraint = self.constraints.pop()

			print constraint

			constraint.resolve(context)
		self.constraints = []
		print

	def dump(self):
		print
		print "="*60

		for context in self.contexts.itervalues():
			context.dump()
			print

def evaluateWithImage(compiler, prgm):
	with compiler.console.scope('ipa analysis'):
		analysis = IPAnalysis(compiler, prgm.storeGraph.canonical)

		for ep, args in prgm.entryPoints:
			analysis.makeFakeEntryPointOp(ep, args)

		while analysis.constraints:
			analysis.resolveConstraints()
			analysis.updateCallGraph()

		analysis.dump()

		assert False

def evaluate(compiler, prgm):
	simpleimagebuilder.build(compiler, prgm)
	return evaluateWithImage(compiler, prgm)
