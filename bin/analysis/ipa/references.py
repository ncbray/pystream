from .. storegraph import setmanager

class Reference(object):
	__slots__ = 'manager', 'values'
	def __init__(self, manager, values=None):
		self.manager = manager
		if values is None: values = manager.setmanager.empty()
		self.values  = values

	def diff(self, other):
		if self.values is other.values:
			result = self.manager.setmanager.empty()
		else:
			result = self.manager.setmanager.diff(self.values, other.values)
		return Reference(self.manager, result)

	def notEmpty(self):
		return bool(self.values)


class ReferenceManager(object):
	def __init__(self):
		self.setmanager = setmanager.CachedSetManager()

	def empty(self):
		return Reference(self)
