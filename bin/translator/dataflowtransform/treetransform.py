from util.typedispatch import *
from language.python import ast

from .. import intrinsics

from util.monkeypatch import xcollections

class ObjectInfo(object):
	def __init__(self, uid):
		self.uid     = uid
		self.objects = []
		self.field   = xcollections.defaultdict(set)

	@property
	def path(self):
		return self.uid[0]

	@property
	def type(self):
		return self.uid[1]

	@property
	def example(self):
		return self.uid[2]


class TreeAnalysis(object):
	def __init__(self, compiler):
		self.compiler = compiler

		self.objectInfo = xcollections.lazydict(lambda obj:  ObjectInfo(obj))
		self.root = set()

		self.current = set()
		self.intrinsicFields = True

	def handleFields(self, obj, objectInfo):
		for slot in obj.slots.itervalues():
			if self.intrinsicFields or not intrinsics.isIntrinsicSlot(slot):
				path = objectInfo.path
				extpath = path + (slot.slotName,)
				objs = self.handleSlot(extpath, slot)
				objectInfo.field[slot.slotName].update(objs)

	def getAbstractInstance(self, example):
		# HACK sometimes constant folding neglects this.
		if not hasattr(example, 'type'):
			self.compiler.extractor.ensureLoaded(example)

		t = example.type
		if not hasattr(t, 'typeinfo'):
			self.compiler.extractor.ensureLoaded(t)

		return t.typeinfo.abstractInstance

	# The policy for object cloning
	def objectUID(self, obj, path):
		# Existing objects should not be cloned.
		xtype = obj.xtype
		pt = xtype.obj.pythonType()

		unique  = True

		example = xtype.obj

		if pt in (float, int):
			# Merge all numeric types
			path = (pt,)
			unique  = False

			# Get the abstract instance of this type
			example = self.getAbstractInstance(example)

		elif xtype.obj.isConcrete():
			# Keep non-numeric existing types unique
			path = (obj,)
		else:
			pass

		uid = path, pt, example

		return uid, unique

	def handleObject(self, obj, path):
		uid, unique = self.objectUID(obj, path)

		objectInfo = self.objectInfo[uid]

		# Keep track of all objects that define their own subtree
		if len(objectInfo.path) <= 1: self.root.add(objectInfo)

		# Have we already considered this obj/path combination?
		if obj not in objectInfo.objects:
			objectInfo.objects.append(obj)

			# Detect recursive cycles
			assert obj not in self.current, obj
			self.current.add(obj)

			self.handleFields(obj, objectInfo)

			self.current.remove(obj)

		return objectInfo

	def handleSlot(self, path, refs):
		objs = []

		for obj in refs:
			objInfo = self.handleObject(obj, path)
			objs.append(objInfo)

		return objs

	def handleLocal(self, lcl, path):
		refs = lcl.annotation.references.merged
		return self.handleSlot(path, refs)


	def process(self, code):
		codeParams = code.codeParameters()

		# Give the self parameter a special name, so we can
		# easily merge it between shaders
		path = ('uniform',)
		self.handleLocal(codeParams.params[0], path)

		for param in codeParams.params[1:]:
			path = (param,)
			self.handleLocal(param, path)


	def dumpObjectInfo(self, objectInfo):
		print objectInfo.uid
		for obj in objectInfo.objects:
			print '\t', obj
		print len(objectInfo.prev), len(objectInfo.next)
		print

	def dump(self):
		for objInfo in self.objectInfo.itervalues():
			self.dumpObjectInfo(objInfo)
		print
		print


from analysis.storegraph import storegraph
from analysis.storegraph import canonicalobjects
from util.graphalgorithim.dominator import dominatorTree

class TreeResynthesis(object):
	def __init__(self, compiler, analysis):
		self.compiler = compiler
		self.analysis = analysis
		self.cache = {}

	def processObject(self, obj):
		if obj not in self.cache:

			example = obj.example

			if obj.example.isAbstract():
				xtype = self.canonical.externalType(example)
			else:
				assert self.count[example] == 1
				xtype = self.canonical.existingType(example)

			if self.count[example] > 1:
				xtype = self.canonical.indexedType(xtype)

			self.cache[obj] = xtype

			graphobj = self.storeGraph.regionHint.object(xtype)

			for fieldName, values in obj.field.iteritems():
				graphfield = graphobj.field(fieldName, self.storeGraph.regionHint)

				for child in values:
					childxtype = self.processObject(child)
					graphfield.initializeType(childxtype)

					self.G[xtype].add(childxtype)

			result = xtype
		else:
			result = self.cache[obj]

		return result

	def countInstances(self):
		count = {}
		for objInfo in self.analysis.objectInfo.itervalues():
			count[objInfo.example] = count.get(objInfo.example, 0)+1
		return count

	def process(self, code):
		self.G = xcollections.defaultdict(set)

		self.count = self.countInstances()

		self.canonical  = canonicalobjects.CanonicalObjects()
		self.storeGraph = storegraph.StoreGraph(self.compiler.extractor, self.canonical)

		# Rewrite memory image
		for obj in self.analysis.root:
			xtype = self.processObject(obj)

			self.G[None].add(xtype)

		# Rewrite entry point
		codeParams = code.codeParameters()
		for param in codeParams.params:
			pass

		tree, idoms = dominatorTree(self.G, None)

		self.dumpTree(None, tree, '')

	def dumpTree(self, node, tree, tabs):
		print "%s%r" % (tabs, node)
		if node in tree:
			for child in tree[node]:
				self.dumpTree(child, tree, tabs+'\t')

def process(compiler, code):
	with compiler.console.scope('analysis'):
		analysis = TreeAnalysis(compiler)
		analysis.process(code)
		#analysis.dump()

	with compiler.console.scope('resynthesis'):
		resynthesis = TreeResynthesis(compiler, analysis)
		resynthesis.process(code)

	with compiler.console.scope('reanalysis'):
		pass
