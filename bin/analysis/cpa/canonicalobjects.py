import util.canonical

from . import base
from . import extendedtypes

class CanonicalObjects(object):
	def __init__(self):
		self.local             = util.canonical.CanonicalCache(base.LocalSlot)
		self.objectSlot        = util.canonical.CanonicalCache(base.ObjectSlot)
		#self.contextObject     = util.canonical.CanonicalCache(extendedtypes.ContextObject)
		self._canonicalContext = util.canonical.CanonicalCache(base.AnalysisContext)
		self.opContext         = util.canonical.CanonicalCache(base.OpContext)
		self.codeContext       = util.canonical.CanonicalCache(base.CodeContext)

		self.cache = {}

	# HACK called from optimization.fold, doesn't create type pointer?
	def externalType(self, obj):
		new = extendedtypes.ExternalObjectType(obj)
		return self.cache.setdefault(new, new)

	def existingType(self, obj):
		new = extendedtypes.ExistingObjectType(obj)
		return self.cache.setdefault(new, new)

	def pathType(self, path, obj):
		new = extendedtypes.PathObjectType(path, obj)
		return self.cache.setdefault(new, new)

	def methodType(self, func, inst, obj):
		new = extendedtypes.MethodContext(func, inst, obj)
		return self.cache.setdefault(new, new)

	def signatureType(self, sig, obj):
		new = extendedtypes.SignatureContext(sig, obj)
		return self.cache.setdefault(new, new)