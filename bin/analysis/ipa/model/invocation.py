import collections
from . import objectname
from .. constraints import flow, qualifiers
from language.python import ast
import itertools

class Invocation(object):
	def __init__(self, src, op, dst):
		self.src = src
		self.op  = op
		self.dst = dst

		self.constraints = []

		self.dst.invokeIn[(src, op)] = self
		self.src.invokeOut[(op, dst)] = self

		self.objForward = {}
		self.objReverse = collections.defaultdict(list)

		self.slotReverse = collections.defaultdict(list)

	def copyDown(self, obj):
		if obj not in self.objForward:
			remapped = self.dst.analysis.objectName(obj.xtype, qualifiers.DN)
			self.objForward[obj] = remapped
			self.objReverse[remapped].append(obj)

			# Copy fields already in use
			region = self.dst.region
			for slot in region.object(remapped).fields.itervalues():
				self.copyFieldFromSourceObj(slot, obj)
		else:
			remapped = self.objForward[obj]

		return remapped

	def copyFieldFromSourceObj(self, slot, prevobj):
		_obj, fieldtype, name = slot.name
		prevfield = self.src.field(prevobj, fieldtype, name)
		self.down(prevfield, slot, fieldTransfer=True)

	def copyFieldFromSources(self, slot):
		obj, _fieldtype, _name = slot.name
		assert obj.isObjectName(), obj

		prev = self.objReverse.get(obj)
		if not prev: return

		for prevobj in prev:
			self.copyFieldFromSourceObj(slot, prevobj)

	def down(self, srcslot, dstslot, fieldTransfer=False):
		assert srcslot.context is self.src
		assert dstslot.context is self.dst

		constraint = flow.DownwardConstraint(self, srcslot, dstslot, fieldTransfer)
		self.constraints.append(constraint)
		constraint.init(self.dst) # HACK?

		if not fieldTransfer:
			self.slotReverse[dstslot].append(srcslot)

	def up(self, srcslot, dstslot):
		assert srcslot.context is self.dst
		assert dstslot.context is self.src

		self.slotReverse[srcslot].append(dstslot)

	def apply(self):
		if self.dst.summary.fresh:
			self.dst.summary.apply(self)

	def upwardSlots(self, slot):
		if slot not in self.slotReverse:
			self.slotReverse[slot].append(self.src.local(ast.Local('summaryTemp')))
		result = self.slotReverse[slot]
		assert result
		return result

	def applyLoad(self, obj, fieldtype, field, dst):
		obj = self.upwardSlots(obj)
		field = self.upwardSlots(field)

		dst = self.upwardSlots(dst)

		# TODO potentially explosive
		for obj, field, dst in itertools.product(obj, field, dst):
			self.src.load(obj, fieldtype, field, dst)

	def applyCopy(self, src, dst):
		src = self.upwardSlots(src)
		dst = self.upwardSlots(dst)

		# TODO potentially explosive
		for src, dst in itertools.product(src, dst):
			self.src.assign(src, dst)

	def translateObjs(self, objs):
		vm = self.src.analysis.valuemanager

		# TODO copy HZ objects up

#		for obj in objs:
#			assert obj.qualifier is qualifiers.GLBL

		return vm.coerce(objs)

	def applyObjs(self, slot, objs):
		objs = self.translateObjs(objs)

		slots = self.upwardSlots(slot)

		for slot in slots:
			slot.updateValues(objs)
