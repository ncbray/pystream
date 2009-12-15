from util.python import uniqueSlotName

class Slots(object):
	def __init__(self):
		self.cache   = {}
		self.reverse = {}
	
	def uniqueSlotName(self, descriptor):
		if descriptor in self.cache:
			return self.cache[descriptor]
					
		uniqueName = uniqueSlotName(descriptor)
		
		self.cache[descriptor]   = uniqueName
		self.reverse[uniqueName] = descriptor
		
		return uniqueName

class CompilerContext(object):
	__slots__ = 'console', 'extractor', 'interface', 'storeGraph', 'liveCode', 'slots'

	def __init__(self, console):
		self.console    = console
		self.extractor  = None
		self.interface  = None
		self.storeGraph = None
		self.liveCode   = None
		self.slots      = Slots()
