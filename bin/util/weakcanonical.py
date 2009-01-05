__all__ = ['WeakCanonical']

import UserDict
from _weakref import ref

class WeakCanonical(object):
	def __init__(self):
		self.data = {}
		
		def removeCallback(k, selfref=ref(self)):
			self = selfref()
			if self is not None:
				del self.data[k]
				
		self._removeCallback = removeCallback

	def get(self, key):
		keywr = ref(key)
		if not keywr in self.data:
			self.data[ref(key, self._removeCallback)] = keywr
			return key
		else:
			return self.data[keywr]()

##	def forget(self, key):
##		del self.data[ref(key)]

	def __repr__(self):
		return "<WeakCanonical at 0x%x>" % id(self)

	def __contains__(self, key):
		try:
			keywr = ref(key)
		except TypeError:
			return False
		return key in self.data

	def __iter__(self):
		for keywr in self.data.iterkeys():
			key = keywr()
			if key is not None:
				yield key
