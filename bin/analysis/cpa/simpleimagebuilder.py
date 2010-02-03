from analysis.storegraph import storegraph, canonicalobjects
from util.python.calling import CallerArgs

class ImageBuilder(object):
	def __init__(self, compiler, prgm):
		self.compiler = compiler
		self.prgm = prgm

		self.allObjects = set()
		self.dirtyObjects = set()

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

		region = self.storeGraph.regionHint
		obj = region.object(xtype)
		self.logObj(obj)
		return obj

	def logObj(self, obj):
		if obj not in self.allObjects:
			self.allObjects.add(obj)
			self.dirtyObjects.add(obj)

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
			return None
		else:
			return [result]

	def resolveEntryPoint(self, entryPoint):
		selfarg = self.handleArg(entryPoint.selfarg)
		args = [self.handleArg(arg) for arg in entryPoint.args]
		kwds = []
		varg = self.handleArg(entryPoint.varg)
		karg = self.handleArg(entryPoint.karg)

		return CallerArgs(selfarg, args, kwds, varg, karg, None)

	def attachAttr(self, root):
		pt = root.xtype.obj.pythonType()

		for t in pt.mro():
			fieldtypes = getattr(t, '__fieldtypes__', None)
			if not isinstance(fieldtypes, dict): continue

			for name, types in fieldtypes.iteritems():
				descriptorName = self.compiler.slots.uniqueSlotName(getattr(pt, name))
				nameObj = self.compiler.extractor.getObject(descriptorName)
				fieldName = self.canonical.fieldName('Attribute', nameObj)
				field = root.field(fieldName, self.storeGraph.regionHint)

				if isinstance(types, type):
					types = (types,)

				for ft in types:
					inst = self.compiler.extractor.getInstance(ft)
					field.initializeType(self.objType(inst))

				for obj in field:
					self.logObj(obj)

	def process(self):
		interface = self.prgm.interface

		for entryPoint in interface.entryPoint:
			args = self.resolveEntryPoint(entryPoint)
			self.entryPoints.append((entryPoint, args))

		while self.dirtyObjects:
			obj = self.dirtyObjects.pop()
			self.attachAttr(obj)


def build(compiler, prgm):
	ib = ImageBuilder(compiler, prgm)
	ib.process()

	prgm.storeGraph  = ib.storeGraph
	prgm.entryPoints = ib.entryPoints
