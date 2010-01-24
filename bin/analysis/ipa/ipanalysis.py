import time

from optimization.callconverter import callConverter
from . constraintextractor import ConstraintExtractor

from . model import objectname
from . model.context import Context
from . constraints import qualifiers
from . calling import cpa

from analysis.storegraph import setmanager

class IPAnalysis(object):
	def __init__(self, compiler, canonical, existingPolicy, externalPolicy):
		self.compiler = compiler
		self.canonical = canonical

		self.existingPolicy = existingPolicy
		self.externalPolicy = externalPolicy

		self.objs = {}
		self.contexts = {}

		self.root = self.getContext(cpa.externalContext)
		self.root.external = True

		self.liveCode = set()

		self.setmanager = setmanager.CachedSetManager()

		self.dirtySlots = []

		self.decompileTime = 0.0

	def pyObj(self, pyobj):
		return self.compiler.extractor.getObject(pyobj)

	def pyObjInst(self, pycls):
		cls = self.pyObj(pycls)
		self.compiler.extractor.ensureLoaded(cls)
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
