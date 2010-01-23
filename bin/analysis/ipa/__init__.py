from language.python import ast, program
from optimization.callconverter import callConverter

from . import constraints, calls, cpacontext
from . constraintextractor import ConstraintExtractor
from . context import Context

from .. cpa import simpleimagebuilder
from .. storegraph import setmanager


class CallBinder(object):
	def __init__(self, call, context):
		self.call    = call
		self.context = context
		self.params  = self.context.signature.code.codeParameters()

		self.invoke = call.context.getInvoke(call.op, context)

	def getSelfArg(self):
		return self.call.selfarg

	def getArg(self, i):
		return self.call.args[i]

	def getVArg(self, i):
		return self.call.varg[i]


	def setSelfParam(self, value):
		typeFilter = self.context.signature.selfparam
		dst = self.context.local(self.params.selfparam)
		self.copyDownFiltered(value, typeFilter, dst)

	def setParam(self, i, value):
		typeFilter = self.context.signature.params[i]
		dst = self.context.local(self.params.params[i])
		self.copyDownFiltered(value, typeFilter, dst)

	def setVParam(self, i, value):
		typeFilter = self.context.signature.vparams[i]
		dst = self.context.vparamTemp[i]
		self.copyDownFiltered(value, typeFilter, dst)


	def copyDownFiltered(self, src, typeFilter, dst):
		# TODO downward?
		self.context.down(self.invoke, src.getFiltered(typeFilter), dst)


class IPAnalysis(object):
	def __init__(self, compiler, canonical):
		self.compiler = compiler
		self.canonical = canonical

		self.objs = {}
		self.contexts = {}

		self.root = self.getContext(cpacontext.externalContext)
		self.root.external = True

		self.constraints = []

		self.sigs = {}

		self.liveCode = set()

		self.setmanager = setmanager.CachedSetManager()

		self.dirtySlots = []

	def dirtySlot(self, slot):
		self.dirtySlots.append(slot)

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
		return self.object(xtype, constraints.GLBL)

	def object(self, xtype, qualifier=constraints.HZ):
		key = (xtype, qualifier)
		if key not in self.objs:
			obj = constraints.AnalysisObject(xtype, qualifier)
			self.objs[key] = obj
		else:
			obj = self.objs[key]
		return obj

	def makeFakeLocal(self, objs):
		if objs is None:
			return None
		else:
			objs = [self.object(xtype) for xtype in objs]
			return self.root.local(ast.Local('entry_point_arg'), objs)

	def makeFakeEntryPointOp(self, ep, epargs):
		selfarg = self.makeFakeLocal(epargs.selfarg)

		args = []
		for arg in epargs.args:
			args.append(self.makeFakeLocal(arg))

		varg = self.makeFakeLocal(epargs.vargs)
		karg = self.makeFakeLocal(epargs.kargs)

		call = self.root.dcall(ep, ep.code, selfarg, args, [], varg, karg, None)

	def getContext(self, sig):
		if sig not in self.contexts:
			context = Context(self, sig)
			self.contexts[sig] = context

			if sig.code:
				context.setup()
				ce = ConstraintExtractor(self, context)
				ce.process()
		else:
			context = self.contexts[sig]
		return context

	def bindCall(self, call, context, info):
		binder = CallBinder(call, context)
		info.transfer(binder, binder)

	def getCode(self, obj):
		assert isinstance(obj, constraints.AnalysisObject)

		extractor = self.compiler.extractor
		code = extractor.getCall(obj.name.obj)
		if code is None:
			code = extractor.stubs.exports['interpreter_call']

		callConverter(extractor, code)

		if code not in self.liveCode:
			self.liveCode.add(code)

		print "code", code

		return code

	def updateCallGraph(self):
		print "update"
		changed = False

		# HACK dictionary size may change...
		for context in tuple(self.contexts.itervalues()):
			changed |= context.updateCallgraph()
		print

		return changed


	def updateConstraints(self):
		print "resolve"
		while self.dirtySlots:
			slot = self.dirtySlots.pop()
			if False:
				print slot
				for value in slot.diff:
					print '\t', value
			slot.propagate()
		print

	def dirtyConstraints(self):
		# HACK self.dirtyCalls?
		return bool(self.dirtySlots)

	def dump(self):
		print
		print "="*60

		for context in self.contexts.itervalues():
			context.dump()
			print

	def topDown(self):
		dirty = True
		while dirty:
			self.updateConstraints()
			self.updateCallGraph()
			dirty = self.dirtyConstraints()


def evaluateWithImage(compiler, prgm):
	with compiler.console.scope('ipa analysis'):
		analysis = IPAnalysis(compiler, prgm.storeGraph.canonical)

		for ep, args in prgm.entryPoints:
			analysis.makeFakeEntryPointOp(ep, args)
			analysis.topDown()

		#analysis.dump()


def evaluate(compiler, prgm):
	simpleimagebuilder.build(compiler, prgm)
	result = evaluateWithImage(compiler, prgm)
	assert False
	return result
