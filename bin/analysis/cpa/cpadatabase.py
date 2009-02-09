import weakref

from . import base

from programIR.python import program, ast

def decontextualizeObjects(objects):
	return frozenset([obj.obj for obj in objects])

class FunctionInfo(object):
	def __init__(self, function):
		self.function    = function
		self.original    = function
		self.descriptive = False
		self.fold        = False
		self.returnSlot  = None

		self.contexts    = set()

		self.opInfos     = weakref.WeakKeyDictionary()
		self.localInfos  = weakref.WeakKeyDictionary()

	def trackRewrite(self, source, dest):
		# TODO make sure this is an op.

		#assert source in self.opInfos, source
		assert not dest in self.opInfos, dest

		info = self.opInfo(source)
		self.opInfos[dest] = info

	def opInfo(self, op):
		assert not isinstance(op, str), op
		if op is None:
			op = base.externalOp

		assert op

		info = self.opInfos.get(op)
		if not info:
			info = ContextualOpInfo()
			self.opInfos[op] = info
		return info

	def localInfo(self, lcl):
		assert lcl

		info = self.localInfos.get(lcl)
		if not info:
			info = ContextualSlotInfo()
			self.localInfos[lcl] = info
		return info

	def merge(self):
		for info in self.opInfos.itervalues():
			info.merge()

		for info in self.localInfos.itervalues():
			info.merge()

class HeapInfo(object):
	def __init__(self, heap):
		self.heap        = heap
		self.original    = heap

		self.contexts    = set()

		self.slotInfos = {}

	def slotInfo(self, slotType, field):
		key = (slotType, field)
		info = self.slotInfos.get(key)
		if not info:
			info = ContextualSlotInfo()
			self.slotInfos[key] = info
		return info

	def merge(self):
		for info in self.slotInfos.itervalues():
			info.merge()

class OpInfo(object):
	__slots__ = 'references', 'invokes'
	def __init__(self):
		self.references = set()
		self.invokes    = set()

	def merge(self, other):
		self.invokes.update(other.invokes)
		self.references.update(other.references)

class ContextualOpInfo(object):
	def __init__(self):
		self.merged = OpInfo()
		self.contexts = {}

	def context(self, context):
		info = self.contexts.get(context)
		if not info:
			info = OpInfo()
			self.contexts[context] = info
		return info

	def merge(self):
		self.merged = OpInfo()
		for info in self.contexts.itervalues():
			self.merged.merge(info)



class ContextualSlotInfo(object):
	def __init__(self):
		self.merged = SlotInfo()
		self.contexts = {}

	def context(self, context):
		info = self.contexts.get(context)
		if not info:
			info = SlotInfo()
			self.contexts[context] = info
		return info

	def merge(self):
		self.merged = SlotInfo()
		for info in self.contexts.itervalues():
			self.merged.merge(info)

class SlotInfo(object):
	def __init__(self):
		self.references = set()

	def merge(self, other):
		self.references.update(other.references)


# Search for object nodes using a depth first search
def getLiveObjectNodes(group):
	objs = set()
	pending = []

	pending.append(group)

	while pending:
		current = pending.pop()
		for slot in current:
			for ref in slot:
				if ref not in objs:
					pending.append(ref)
					objs.add(ref)
	return objs

class CPADatabase(object):
	def __init__(self):
		self.functionInfos = weakref.WeakKeyDictionary()
		self.heapInfos    = weakref.WeakKeyDictionary()


	def contextOpInfo(self, function, op, context):
		return self.functionInfo(function).opInfo(op).context(context)

	def functionInfo(self, func):
		assert not isinstance(func, str), func
		if not func in self.functionInfos:
			info = FunctionInfo(func)
			self.functionInfos[func] = info
		else:
			info = self.functionInfos[func]
		return info

	def heapInfo(self, heap):
		if not heap in self.heapInfos:
			info = HeapInfo(heap)
			self.heapInfos[heap] = info
		else:
			info = self.heapInfos[heap]
		return info

	def loadObjects(self, sys):
		# Find the live object nodes
		objs = getLiveObjectNodes(sys.roots)

		# Build the database
		self.liveObjectGroups = set()
		dynamic = 0
		for obj in objs:
			ogroup = obj.xtype.group()
			self.liveObjectGroups.add(ogroup)

			hinfo = self.heapInfo(ogroup)
			hinfo.contexts.add(obj)

			# Index the slots
			for slot in obj:
				slotName = slot.slotName
				info = hinfo.slotInfo(slotName.type, slotName.name).context(obj)
				info.references.update(slot)

			if not obj.xtype.isExisting() and not obj.xtype.isExternal():
				dynamic += 1


		sys.console.output("%d heap objects." % len(objs))
		sys.console.output("%d groups." % len(self.liveObjectGroups))
		sys.console.output("%.1f%% dynamic" % (float(dynamic)/max(len(objs), 1)*100.0))


	def finalizeInfos(self):
		# Finalize the datastructures
		for info in self.functionInfos.itervalues():
			info.merge()

		for info in self.heapInfos.itervalues():
			info.merge()

	def load(self, sys):
		for code, contexts in sys.codeContexts.iteritems():
			info = self.functionInfo(code)
			info.contexts.update(contexts)

		for srcop, dsts in sys.opInvokes.iteritems():
			assert isinstance(dsts, set)
			for dstfunc in dsts:
				# src -> dst
				info = self.contextOpInfo(srcop.code, srcop.op, srcop.context)
				info.invokes.add((dstfunc.context, dstfunc.code))

				# dst <- src
				info = self.functionInfo(dstfunc.code)
				info.contexts.add(dstfunc.context)

		self.loadObjects(sys)


		# Find all the locals
		for slot in sys.roots:
			name = slot.slotName
			if name.isLocal():
				info = self.functionInfo(name.code).localInfo(name.local).context(name.context)
				info.references.update(slot)
			elif name.isExisting():
				info = self.functionInfo(name.code).localInfo(name.object).context(name.context)
				info.references.update(slot)


		self.finalizeInfos()

	def liveFunctions(self):
		return set(self.functionInfos.keys())

	def liveObjects(self):
		return self.liveObjectGroups

	def iterContextOp(self):
		for func, funcInfo in self.functionInfos.iteritems():
			for op, opInfos in funcInfo.opInfos.iteritems():
				for context, cInfo in opInfos.contexts.iteritems():
					yield func, op, context, cInfo

