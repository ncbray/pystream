import util.canonical
from language.python import program
from . import extendedtypes
from util.monkeypatch import xcollections

class BaseSlotName(util.canonical.CanonicalObject):
	__slots__ = ()

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
		assert code.isCode(), type(code)
#		assert context.isAnalysisContext(), type(context)

		self.code    = code
		self.local   = lcl
		self.context = context
		self.setCanonical(code, lcl, context)

	def isRoot(self):
		return True

	def isLocal(self):
		return True

	def __repr__(self):
		return 'local(%s, %r, %d)' % (self.code.codeName(), self.local, id(self.context))


class ExistingSlotName(BaseSlotName):
	__slots__ = 'code', 'object', 'context'

	def __init__(self, code, object, context):
		assert code.isCode(), type(code)
#		assert isinstance(obj, program.AbstractObject), type(obj)
#		assert context.isAnalysisContext(), type(context)

		self.code    = code
		self.object     = object
		self.context = context
		self.setCanonical(code, object, context)

	def isRoot(self):
		return True

	def isExisting(self):
		return True

	def __repr__(self):
		return 'existing(%s, %r, %d)' % (self.code.codeName(), self.object, id(self.context))


class FieldSlotName(BaseSlotName):
	__slots__ = 'type', 'name'
	def __init__(self, ftype, name):
		assert isinstance(ftype, str), type(ftype)
		assert isinstance(name, program.AbstractObject), type(name)

		self.type = ftype
		self.name = name
		self.setCanonical(ftype, name)

	def isField(self):
		return True

	def __repr__(self):
		return 'field(%s, %r)' % (self.type, self.name)


class OpContext(util.canonical.CanonicalObject):
	__slots__ ='code', 'op', 'context',
	def __init__(self, code, op, context):
		assert code.isCode(), type(code)
		assert context.isAnalysisContext(), type(context)

		self.setCanonical(code, op, context)

		self.code     = code
		self.op       = op
		self.context  = context


class CodeContext(util.canonical.CanonicalObject):
	__slots__ = 'code', 'context',
	def __init__(self, code, context):
		assert code.isCode(), type(code)
		assert context.isAnalysisContext(),type(context)

		self.setCanonical(code, context)

		self.code     = code
		self.context  = context

	def decontextualize(self):
		return self.code


class CanonicalObjects(object):
	def __init__(self):
		self.opContext   = util.canonical.CanonicalCache(OpContext)
		self.codeContext = util.canonical.CanonicalCache(CodeContext)
		self.cache       = xcollections.weakcache()

		self.index = 0

	def localName(self, code, lcl, context):
		return self.cache[LocalSlotName(code, lcl, context)]

	def existingName(self, code, obj, context):
		return self.cache[ExistingSlotName(code, obj, context)]

	def fieldName(self, type, fname):
		return self.cache[FieldSlotName(type, fname)]

	def externalType(self, obj):
		return self.cache[extendedtypes.ExternalObjectType(obj, None)]

	def existingType(self, obj):
		return self.cache[extendedtypes.ExistingObjectType(obj, None)]

	def pathType(self, path, obj, op):
		return self.cache[extendedtypes.PathObjectType(path, obj, op)]

	def methodType(self, func, inst, obj, op):
		return self.cache[extendedtypes.MethodObjectType(func, inst, obj, op)]

	def contextType(self, sig, obj, op):
		return self.cache[extendedtypes.ContextObjectType(sig, obj, op)]

	def indexedType(self, xtype):
		# Remove indexed object wrappers
		while isinstance(xtype, extendedtypes.IndexedObjectType):
			xtype = xtype.xtype

		index = self.index
		self.index += 1

		return self.cache[extendedtypes.IndexedObjectType(xtype, index)]
