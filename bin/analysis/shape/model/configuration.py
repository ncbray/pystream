# TODO special object == null pointer?
class Configuration(object):
	__slots__ = 'object', 'region', 'entrySet', 'currentSet'
	def __init__(self, object_, region, entrySet, currentSet):
		self.object     = object_
		self.region     = region
		self.entrySet   = entrySet
		self.currentSet = currentSet

	def referedToBySlot(self, slot):
		return self.currentSet.referedToBySlot(slot)

	def isConfiguration(self):
		return True

	def __repr__(self):
		return "conf(object=%r, entry=%r, exit=%r)" % (self.object, self.entrySet, self.currentSet)

	def incrementRef(self, sys, slot):
		newrefs = sys.canonical.incrementRef(self.currentSet, slot)
		return [sys.canonical.configuration(self.object, self.region, self.entrySet, current) for current in newrefs]

	def decrementRef(self, sys, slot):
		newrefs = sys.canonical.decrementRef(self.currentSet, slot)
		return [sys.canonical.configuration(self.object, self.region, self.entrySet, current) for current in newrefs]
