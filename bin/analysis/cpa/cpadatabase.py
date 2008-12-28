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
		
		#self.slotInfos  = weakref.WeakKeyDictionary()
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
	def __init__(self):
		self.references = set()
		self.reads      = set()
		self.modifies   = set()
		self.allocates  = set()
		self.invokes    = set()

	def merge(self, other):
		self.allocates.update(other.allocates)
		self.reads.update(other.reads)
		self.modifies.update(other.modifies)
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

	def load(self, sys):
		for func, contexts in sys.functionContexts.iteritems():
			info = self.functionInfo(func)
			info.contexts.update(contexts)

		for heap, contexts in sys.heapContexts.iteritems():
			info = self.heapInfo(heap)
			info.contexts.update(contexts)


		for srcop, dstfunc in sys.invocations:
			info = self.functionInfo(dstfunc.function)
			info.contexts.add(dstfunc.context)

			info = self.contextOpInfo(srcop.function, srcop.op, srcop.context)
			info.invokes.add((dstfunc.context, dstfunc.function))

		for slot, values in sys.slots.iteritems():
			if slot.isLocalSlot():
				if not isinstance(slot.local, program.AbstractObject):
					if isinstance(slot.local, ast.Local):
						info = self.functionInfo(slot.function).localInfo(slot.local).context(slot.context)
					else:
						info = self.functionInfo(slot.function).opInfo(slot.local).context(slot.context)
					info.references.update(values)
			else:
				info = self.heapInfo(slot.obj.obj).slotInfo(slot.slottype, slot.key).context(slot.obj.context)
				info.references.update(values)
	
		for cop, slots in sys.la.rm.opReads.iteritems():
			info = self.contextOpInfo(cop.function, cop.op, cop.context)
			info.reads.update(slots)

		for cop, slots in sys.la.rm.opModifies.iteritems():
			info = self.contextOpInfo(cop.function, cop.op, cop.context)
			info.modifies.update(slots)

		# Allocates?

		# Finalize the datastructures
		for info in self.functionInfos.itervalues():
			info.merge()
			
		for info in self.heapInfos.itervalues():
			info.merge()

	def liveFunctions(self):
		return set(self.functionInfos.keys())


	def iterContextOp(self):
		for func, funcInfo in self.functionInfos.iteritems():
			for op, opInfos in funcInfo.opInfos.iteritems():
				for context, cInfo in opInfos.contexts.iteritems():
					yield func, op, context, cInfo

