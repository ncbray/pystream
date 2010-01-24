import collections
from . import objectname
from .. constraints import flow, qualifiers

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

	def copyDown(self, obj):
		# TODO copy down existing fields
		if obj not in self.objForward:
			remapped = self.dst.analysis.objectName(obj.xtype, qualifiers.DN)
			self.objForward[obj] = remapped
			self.objReverse[remapped].append(obj)

			# Copy fields already in use
			region = self.dst.region
			for slot in region.object(remapped).fields.itervalues():
				print "old slot", slot
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
