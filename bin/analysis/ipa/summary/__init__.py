from ..constraints import qualifiers
import collections

class SummaryCopy(object):
	def __init__(self, src, dst):
		self.src = src
		self.dst = dst

	def apply(self, invoke):
		invoke.applyCopy(self.src, self.dst)

class SummaryLoad(object):
	def __init__(self, obj, fieldtype, field, dst):
		self.obj = obj
		self.fieldtype = fieldtype
		self.field = field
		self.dst = dst

	def apply(self, invoke):
		invoke.applyLoad(self.obj, self.fieldtype, self.field, self.dst)

class Summary(object):
	def __init__(self):
		self.slots = {}
		self.ops   = []
		self.slotObjs = collections.defaultdict(list)

		self.dirty = False
		self.fresh = False

	def reset(self):
		self.slots = {}
		self.ops   = []
		self.slotObjs = collections.defaultdict(list)

	def copy(self, src, dst):
		self.ops.append(SummaryCopy(src, dst))

	def load(self, obj, fieldtype, field, dst):
		self.ops.append(SummaryLoad(obj, fieldtype, field, dst))

	def handleObjects(self, context, slot):
		for obj in slot.values:

			if obj.qualifier is qualifiers.HZ:
				# TODO copy fields
				self.slotObjs[slot].append(obj)
			elif obj.qualifier is qualifiers.GLBL:
				self.slotObjs[slot].append(obj)

	def handleSlot(self, context, slot):
		if slot not in self.slots:
			context.summary.slots[slot] = slot

			for prev in slot.critical.values:
				if prev is not slot.name:
					prevSlot = context.local(prev)
					self.handleSlot(context, prevSlot)
					self.copy(prevSlot, slot)

			for prevOp in slot.prev:
				if prevOp.isLoad() and prevOp.obj.critical.isCritical:
					self.handleSlot(context, prevOp.obj)
					self.handleSlot(context, prevOp.field)
					self.load(prevOp.obj, prevOp.fieldtype, prevOp.field, slot)

			self.handleObjects(context, slot)

	def apply(self, invoke):
		for op in self.ops:
			op.apply(invoke)

		for slot, objs in self.slotObjs.iteritems():
			invoke.applyObjs(slot, objs)

def update(context):
	summary = context.summary
	if not summary.dirty:
		return

	summary.dirty = False
	summary.fresh = True

	context.summary.reset() # HACK not incremental

	for param in context.returns:
		context.summary.handleSlot(context, param)

	assert not context.criticalStores
