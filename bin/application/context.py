class CompilerContext(object):
	__slots__ = 'console', 'extractor', 'interface', 'storeGraph', 'liveCode'

	def __init__(self, console):
		self.console    = console
		self.extractor  = None
		self.interface  = None
		self.storeGraph = None
		self.liveCode   = None
