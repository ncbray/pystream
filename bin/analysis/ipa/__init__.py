import time
from optimization.callconverter import callConverter

from . constraints import flow, calls, qualifiers
from . model import objectname
from . model.context import Context
from . calling import cpa
from . constraintextractor import ConstraintExtractor
from . entrypointbuilder import buildEntryPoint

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

		self.liveCode = set()

		self.setmanager = setmanager.CachedSetManager()

		self.dirtySlots = []

		self.decompileTime = 0.0

	def tupleInstance(self):
		tupleCls = self.pyObj(tuple)
		self.compiler.extractor.ensureLoaded(tupleCls)
		return tupleCls.typeinfo.abstractInstance

	def pyObj(self, pyobj):
		return self.compiler.extractor.getObject(pyobj)

	def objectName(self, xtype, qualifier=qualifiers.HZ):
		key = (xtype, qualifier)
		if key not in self.objs:
			obj = objectname.ObjectName(xtype, qualifier)
			self.objs[key] = obj
		else:
			obj = self.objs[key]
		return obj

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
		start = time.clock()

		assert isinstance(obj, objectname.ObjectName)

		extractor = self.compiler.extractor
		code = extractor.getCall(obj.xtype.obj)
		if code is None:
			code = extractor.stubs.exports['interpreter_call']

		callConverter(extractor, code)

		if code not in self.liveCode:
			self.liveCode.add(code)

		end = time.clock()
		self.decompileTime += end-start

		return code

	### Analysis methods ###

	def dirtySlot(self, slot):
		self.dirtySlots.append(slot)

	def dirtyConstraints(self):
		return bool(self.dirtySlots)

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

	def topDown(self):
		dirty = True
		while dirty:
			self.updateConstraints()
			self.updateCallGraph()
			dirty = self.dirtyConstraints()


def dumpAnalysisResults(analysis):
	dumper = Dumper('summaries/ipa')

	dumper.index(analysis.contexts.values(), analysis.root)

	for context in analysis.contexts.itervalues():
		dumper.dumpContext(context)


def evaluateWithImage(compiler, prgm):
	with compiler.console.scope('ipa analysis'):
		analysis = IPAnalysis(compiler, prgm.storeGraph)

		for ep, args in prgm.entryPoints:
			buildEntryPoint(analysis, ep, args)

		analysis.topDown()

		print "%5d code" % len(analysis.liveCode)
		print "%5d contexts" % len(analysis.contexts)
		print "%.2f ms decompile" % (analysis.decompileTime*1000.0)

	with compiler.console.scope('ipa dump'):
		dumpAnalysisResults(analysis)


def evaluate(compiler, prgm):
	simpleimagebuilder.build(compiler, prgm)
	result = evaluateWithImage(compiler, prgm)
	return result
