import util.canonical

from . import extendedtypes
from . import base

from programIR.python import program, ast

class BaseSlotName(util.canonical.CanonicalObject):
	__slots__ =()

	def isRoot(self):
		return False

	def isLocal(self):
		return False

	def isExisting(self):
		return False

	def isField(self):
		return False


class LocalSlotName(BaseSlotName):
	__slots__ = 'code', 'local', 'context'
	def __init__(self, code, lcl, context):
#		assert isinstance(code, ast.Code), type(code)
#		assert isinstance(lcl, ast.Local), type(lcl)
#		assert isinstance(context, base.AnalysisContext), type(context)

		self.code    = code
		self.local   = lcl
		self.context = context
		self.setCanonical(code, lcl, context)

	def isRoot(self):
		return True

	def isLocal(self):
		return True

	def __repr__(self):
		return 'local(%s, %r, %d)' % (self.code.name, self.local, id(self.context))


class ExistingSlotName(BaseSlotName):
	__slots__ = 'code', 'obj', 'context'

	def __init__(self, code, obj, context):
#		assert isinstance(code, ast.Code), type(code)
#		assert isinstance(obj, program.AbstractObject), type(obj)
#		assert isinstance(context, base.AnalysisContext), type(context)

		self.code    = code
		self.obj     = obj
		self.context = context
		self.setCanonical(code, obj, context)

	def isRoot(self):
		return True

	def isExisting(self):
		return True

	def __repr__(self):
		return 'existing(%s, %r, %d)' % (self.code.name, self.obj, id(self.context))


class FieldSlotName(BaseSlotName):
	__slots__ = 'type', 'name'
	def __init__(self, ftype, name):
#		assert isinstance(ftype, str), type(ftype)
#		assert isinstance(name, program.AbstractObject), type(name)

		self.type = ftype
		self.name = name
		self.setCanonical(ftype, name)

	def isField(self):
		return True

	def __repr__(self):
		return 'field(%s, %r)' % (self.type, self.name)



class CanonicalObjects(object):
	def __init__(self):
		#self.local             = util.canonical.CanonicalCache(base.LocalSlot)
		#self.objectSlot        = util.canonical.CanonicalCache(base.ObjectSlot)
		self._canonicalContext = util.canonical.CanonicalCache(base.AnalysisContext)
		self.opContext         = util.canonical.CanonicalCache(base.OpContext)
		self.codeContext       = util.canonical.CanonicalCache(base.CodeContext)

		self.cache = {}

	def localName(self, code, lcl, context):
		name = LocalSlotName(code, lcl, context)
		return self.cache.setdefault(name, name)

	def existingName(self, code, obj, context):
		name = ExistingSlotName(code, obj, context)
		return self.cache.setdefault(name, name)


	def fieldName(self, type, fname):
		name = FieldSlotName(type, fname)
		return self.cache.setdefault(name, name)


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