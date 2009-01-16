from . import pathinformation

class SecondaryInformation(object):
	__slots__ = 'paths', 'externalReferences'
	def __init__(self, paths, externalReferences):
		self.paths = paths
		self.externalReferences = externalReferences

	def merge(self, other):
		paths, pathsChanged = self.paths.inplaceMerge(other.paths)
		if pathsChanged:
			self.paths = paths

		if self.externalReferences == False and other.externalReferences == True:
			self.externalReferences = True
			externalChanged = True
		else:
			externalChanged = False

		return pathsChanged or externalChanged

	def __repr__(self):
		return "secondary(..., external=%r)" % (self.externalReferences,)

	def copy(self):
		return SecondaryInformation(self.paths.copy(), self.externalReferences)

	def forget(self, sys, kill):
		return sys.canonical.secondary(self.paths.forget(kill), self.externalReferences)
