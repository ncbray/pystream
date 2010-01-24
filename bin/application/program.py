from . import interface

class Program(object):
	__slots__ = 'interface', 'storeGraph', 'entryPoints', 'liveCode'

	def __init__(self):
		self.interface = interface.InterfaceDeclaration()