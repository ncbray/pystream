from language.python import ast, program
from optimization.callconverter import callConverter

from . constraints import flow, calls, qualifiers
from . model import objectname
from . model.context import Context
from . calling import cpa
from . constraintextractor import ConstraintExtractor

from analysis.cpa import simpleimagebuilder
from analysis.storegraph import setmanager

from .dump import Dumper

class IPAnalysis(object):
	def __init__(self, compiler, storeGraph):
		self.compiler = compiler
		self.storeGraph = storeGraph
		self.canonical = storeGraph.canonical

		self.objs = {}
		self.contexts = {}

		self.root = self.getContext(cpa.externalContext)
		self.root.external = True

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

	def canonicalSignature(self, sig):
		return self.sigs.setdefault(sig, sig)

	def pyObj(self, pyobj):
		obj = self.compiler.extractor.getObject(pyobj)
		xtype = self.canonical.existingType(obj)
		return self.object(xtype, qualifiers.GLBL)

	def object(self, xtype, qualifier=qualifiers.HZ):
		key = (xtype, qualifier)
		if key not in self.objs:
			obj = objectname.ObjectName(xtype, qualifier)
			self.objs[key] = obj
		else:
			obj = self.objs[key]
		return obj

	def makeFakeLocal(self, objs):
		if objs is None:
			return None
		else:
			lcl = self.root.local(ast.Local('entry_point_arg'))
			objs = frozenset([self.object(xtype) for xtype in objs])
			lcl.updateValues(objs)
			return lcl

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

	def getCode(self, obj):
		assert isinstance(obj, objectname.ObjectName)

		extractor = self.compiler.extractor
		code = extractor.getCall(obj.xtype.obj)
		if code is None:
			code = extractor.stubs.exports['interpreter_call']

		callConverter(extractor, code)

		if code not in self.liveCode:
			self.liveCode.add(code)

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
		dumper = Dumper('summaries/ipa')

		dumper.index(self.contexts.values(), self.root)

		for context in self.contexts.itervalues():
			dumper.dumpContext(context)

	def topDown(self):
		dirty = True
		while dirty:
			self.updateConstraints()
			self.updateCallGraph()
			dirty = self.dirtyConstraints()


def evaluateWithImage(compiler, prgm):
	with compiler.console.scope('ipa analysis'):
		analysis = IPAnalysis(compiler, prgm.storeGraph)

		for ep, args in prgm.entryPoints:
			analysis.makeFakeEntryPointOp(ep, args)
			analysis.topDown()

		print "%5d code" % len(analysis.liveCode)
		print "%5d contexts" % len(analysis.contexts)

	with compiler.console.scope('ipa dump'):
		analysis.dump()


def evaluate(compiler, prgm):
	simpleimagebuilder.build(compiler, prgm)
	result = evaluateWithImage(compiler, prgm)
	return result
