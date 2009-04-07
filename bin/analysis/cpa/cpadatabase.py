import weakref

from . import base

from language.python import program, ast


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
		self.heapInfos     = weakref.WeakKeyDictionary()
		self.liveCode      = set()

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
		for info in self.heapInfos.itervalues():
			info.merge()

	def load(self, sys):
		self.liveCode.update(sys.codeContexts.iterkeys())
		self.loadObjects(sys)
		self.finalizeInfos()

	def liveFunctions(self):
		return self.liveCode

	def liveObjects(self):
		return self.liveObjectGroups