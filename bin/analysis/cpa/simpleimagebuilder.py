from analysis.storegraph import storegraph, canonicalobjects
from util.python.calling import CallerArgs

class ImageBuilder(object):
	def __init__(self, compiler):
		self.compiler = compiler
		self.canonical  = canonicalobjects.CanonicalObjects()
		self.storeGraph = storegraph.StoreGraph(self.compiler.extractor, self.canonical)
		self.entryPoints = []

	def objType(self, obj):
		self.ensureLoaded(obj)
		if obj.isAbstract():
			return self.canonical.externalType(obj)
		else:
			return self.canonical.existingType(obj)

	def objGraphObj(self, obj):
		xtype  = self.objType(obj)
		return self.storeGraph.regionHint.object(xtype)

	def ensureLoaded(self, obj):
		# HACK sometimes constant folding neglects this.
		if not hasattr(obj, 'type'):
			self.compiler.extractor.ensureLoaded(obj)

		t = obj.type
		if not hasattr(t, 'typeinfo'):
			self.compiler.extractor.ensureLoaded(t)

	def addAttr(self, src, attrName, dst):
		obj = self.objGraphObj(src)

		fieldName = self.canonical.fieldName(*attrName)
		field = obj.field(fieldName, self.storeGraph.regionHint)

		field.initializeType(self.objType(dst))

	def getExistingSlot(self, pyobj):
		obj = self.compiler.extractor.getObject(pyobj)
		return self.objGraphObj(obj).xtype

	def getInstanceSlot(self, typeobj):
		obj = self.compiler.extractor.getInstance(typeobj)
		return self.objGraphObj(obj).xtype

	def handleArg(self, arg):
		# Assumes args are not polymorphic!  (True for now)
		result = arg.get(self)
		if result is None:
			return []
		else:
			return [result]

	def resolveEntryPoint(self, entryPoint):
		selfarg = self.handleArg(entryPoint.selfarg)
		args = [self.handleArg(arg) for arg in entryPoint.args]
		kwds = []
		varg = self.handleArg(entryPoint.varg)
		karg = self.handleArg(entryPoint.karg)

		return CallerArgs(selfarg, args, kwds, varg, karg, None)

	def process(self):
		interface = self.compiler.interface

		for src, attrName, dst in interface.attr:
			self.addAttr(src, attrName, dst)

		for entryPoint in interface.entryPoint:
			args = self.resolveEntryPoint(entryPoint)

			self.entryPoints.append((entryPoint, args))

def build(compiler):
	ib = ImageBuilder(compiler)
	ib.process()
	return ib.storeGraph, ib.entryPoints
