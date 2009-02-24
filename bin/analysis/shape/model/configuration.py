# TODO special object == null pointer?
class Configuration(object):
	__slots__ = 'object', 'region', 'entrySet', 'currentSet', 'externalReferences'
	def __init__(self, object_, region, entrySet, currentSet, externalReferences):
		self.object     = object_
		self.region     = region
		self.entrySet   = entrySet
		self.currentSet = currentSet
		self.externalReferences = externalReferences

	def slotHit(self, slot):
		return self.currentSet.slotHit(slot)

	def isConfiguration(self):
		return True

	def __repr__(self):
		return "conf(object=%r, entry=%r, current=%r, ex=%r)" % (self.object, self.entrySet, self.currentSet, self.externalReferences)

	def incrementRef(self, sys, slot):
		newrefs = sys.canonical.incrementRef(self.currentSet, slot)
		return [sys.canonical.configuration(self.object, self.region, self.entrySet, current, self.externalReferences) for current in newrefs]

	def decrementRef(self, sys, slot):
		newrefs = sys.canonical.decrementRef(self.currentSet, slot)
		return [sys.canonical.configuration(self.object, self.region, self.entrySet, current, self.externalReferences) for current in newrefs]

	def forget(self, sys, kill):
		currentSet = self.currentSet.forget(sys, kill)
		return sys.canonical.configuration(self.object, self.region, self.entrySet, currentSet, self.externalReferences)
