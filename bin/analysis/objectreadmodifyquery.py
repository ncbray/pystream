import collections
from programIR.python import ast


# TODO not sound for external side effects? (Only pays attention to load/stores.)
# TODO not sound for varg/karg munging

class ObjectReadModifyQuery(object):
	def __init__(self, db):
		self.slotRead     = set()
		self.slotModify   = set()
		self.objectRead   = set()
		self.objectModify = set()
		
		for func, op, context, info in db.iterContextOp():
			if isinstance(op, ast.Load):
				for slot in info.reads:
					self.slotRead.add(slot)
					self.objectRead.add(slot.obj)

			if isinstance(op, ast.Store):
				for slot in info.modifies:
					self.slotModify.add(slot)
					self.objectModify.add(slot.obj)


		for slot in self.slotRead:
			print slot
		print
