import time

from optimization.callconverter import callConverter
from . import constraintextractor

from . model import objectname
from . model.context import Context
from . constraints import qualifiers
from . calling import cpa

from analysis.storegraph import setmanager

from . escape import objectescape

class IPAnalysis(object):
	def __init__(self, extractor, canonical, existingPolicy, externalPolicy):
		self.extractor = extractor
		self.canonical = canonical

		self.existingPolicy = existingPolicy
		self.externalPolicy = externalPolicy

		self.objs = {}
		self.contexts = {}

		self.root = self.getContext(cpa.externalContext)
		self.root.external = True

		self.liveCode = set()

		self.valuemanager    = setmanager.CachedSetManager()
		self.criticalmanager = setmanager.CachedSetManager()

		self.dirtySlots = []

		self.decompileTime = 0.0

		self.trace = False

	def pyObj(self, pyobj):
		return self.extractor.getObject(pyobj)

	def pyObjInst(self, pycls):
		cls = self.pyObj(pycls)
		self.extractor.ensureLoaded(cls)
		return cls.typeinfo.abstractInstance

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

			if sig and sig.code:
				constraintextractor.evaluate(self, context, sig.code)
		else:
			context = self.contexts[sig]
		return context

	def getCode(self, obj):
		start = time.clock()

		assert obj.isObjectName()

		code = self.extractor.getCall(obj.obj())
		if code is None:
			code = self.extractor.stubs.exports['interpreter_call']

		callConverter(self.extractor, code)

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
		if self.trace: print "update"
		changed = False

		# HACK dictionary size may change...
		for context in tuple(self.contexts.itervalues()):
			changed |= context.updateCallgraph()
		if self.trace: print

		return changed

	def updateConstraints(self):
		if self.trace: print "resolve"
		while self.dirtySlots:
			slot = self.dirtySlots.pop()
			slot.propagate()
		if self.trace: print

	def topDown(self):
		dirty = True
		while dirty:
			self.updateConstraints()
			self.updateCallGraph()
			dirty = self.dirtyConstraints()

	def propagateCriticals(self, context):
		while context.dirtycriticals:
			node = context.dirtycriticals.pop()
			node.critical.propagate(context, node)

	def contextBottomUp(self, context):
		if context not in self.processed:
			self.processed.add(context)
			self.path.append(context)

			# Process children first
			for invoke in context.invokeOut.itervalues():
				self.contextBottomUp(invoke.dst)

			self.propagateCriticals(context)
			objectescape.process(context)

			self.path.pop()
		else:
			assert context not in self.path, "Recursive cycle detected in call graph"

	def bottomUp(self):
		self.processed = set()
		self.path = []

		self.contextBottomUp(self.root)
