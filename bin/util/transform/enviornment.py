from base import *

class Enviornment(object):
	def __init__(self, parent=None):
		assert parent == None or isinstance(parent, Enviornment)
		
		self.parent = parent
		self.env = {}

	def read(self, name):
		assert isinstance(name, str), name
		if name in self.env:
			return self.env[name]
		elif self.parent != None:
			return self.parent.read(name)
		else:
			raise Exception, "Attempted to read non-existant value %s" % repr(name)

	def contains(self, name):
		assert isinstance(name, str), name
		if name in self.env:
			return True, self.env[name] 
		elif self.parent != None:
			return self.parent.contains(name)
		else:
			return False, None

	def bind(self, name, value):
		assert isinstance(name, str), name

		if not name in self.env:
			self.env[name] = value
		else:
			if not self.env[name] == value:
				return doFail()
		return value

	def child(self):
		return Enviornment(self)

	# HACK
	def new(self):
		return Enviornment()
