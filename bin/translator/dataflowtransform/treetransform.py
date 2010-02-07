from util.typedispatch import *
from language.python import ast

from .. import intrinsics

from util.monkeypatch import xcollections
from util.python.calling import CallerArgs

from analysis import cpa, lifetimeanalysis

from application.program import Program

class ReadCollector(TypeDispatcher):
	def __init__(self):
		self.reads = set()

	@dispatch(ast.leafTypes, ast.CodeParameters, ast.Local, ast.Existing, ast.Return)
	def visitLeaf(self, node):
		pass

	@dispatch(ast.Load, ast.Store, ast.Allocate, ast.Call, ast.DirectCall)
	def visitOP(self, node):
		self.reads.update(node.annotation.reads.merged)

	@dispatch(ast.Assign, ast.Discard)
	def visitAssign(self, node):
		self(node.expr)

	@dispatch(ast.Suite, ast.Switch, ast.Condition, ast.TypeSwitch, ast.TypeSwitchCase, ast.While)
	def visitOK(self, node):
		node.visitChildren(self)

	def process(self, code):
		code.visitChildrenForced(self)

class ObjectInfo(object):
	def __init__(self, uid):
		self.uid     = uid
		self.objects = []
		self.field   = xcollections.defaultdict(set)
		self.result  = None

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
	def __init__(self, compiler, reads):
		self.compiler = compiler
		self.reads = reads

		self.objectInfo = xcollections.lazydict(lambda obj:  ObjectInfo(obj))
		self.root = set()

		self.current = set()
		self.intrinsicFields = True

	def handleFields(self, obj, objectInfo):
		for slot in obj.slots.itervalues():

			intrinsic = intrinsics.isIntrinsicSlot(slot)
			slotRead = slot in self.reads

			if self.intrinsicFields and intrinsic or slotRead and not intrinsic:
				path = objectInfo.path
				extpath = path + (slot.slotName,)
				objs = self.handleSlot(extpath, slot)
				objectInfo.field[slot.slotName].update(objs)

	def ensureLoaded(self, example):
		# HACK sometimes constant folding neglects this.
		if not hasattr(example, 'type'):
			self.compiler.extractor.ensureLoaded(example)

		t = example.type
		if not hasattr(t, 'typeinfo'):
			self.compiler.extractor.ensureLoaded(t)

	def getAbstractInstance(self, example):
		self.ensureLoaded(example)
		return example.type.typeinfo.abstractInstance

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


	def handleParam(self, param, pathname=None):
		if param is None: return None
		if param.isDoNotCare(): return None # TODO is this correct?
		if pathname is None: pathname = param
		return self.handleLocal(param, (pathname,))


	def process(self, code):
		codeParams = code.codeParameters()

		selfparam = (codeParams.selfparam, self.handleParam(codeParams.selfparam))


		params = []

		# Give the self parameter a special name, so we can
		# easily merge it between shaders
		uniformParam = codeParams.params[0]
		params.append((uniformParam, self.handleParam(uniformParam, 'uniform')))

		for param in codeParams.params[1:]:
			params.append((param, self.handleParam(param)))

		vparam = (codeParams.vparam, self.handleParam(codeParams.vparam))
		kparam = (codeParams.kparam, self.handleParam(codeParams.kparam))

		return CallerArgs(selfparam, params, [], vparam, kparam, None)

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
from util.graphalgorithim import exclusiongraph

class TreeResynthesis(object):
	def __init__(self, compiler, analysis):
		self.compiler = compiler
		self.analysis = analysis

		self.canonical  = canonicalobjects.CanonicalObjects()
		self.storeGraph = storegraph.StoreGraph(self.compiler.extractor, self.canonical)

		self.shaderprgm = Program()
		self.shaderprgm.storeGraph = self.storeGraph
		self.shaderprgm.entryPoints = []

		self.roots = []

		self.cache = {}

	def processObject(self, obj):
		if obj is None: return None

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

			assert xtype.obj.pythonType() is not list, "lists create non-uniqueness, currently unsupported."

			graphobj = self.storeGraph.regionHint.object(xtype)
			graphobj.rewriteAnnotation(preexisting=True, unique=True, final=True)

			for fieldName, values in obj.field.iteritems():
				graphfield = graphobj.field(fieldName, self.storeGraph.regionHint)

				for child in values:
					childxtype = self.processObject(child)
					graphfield.initializeType(childxtype)
					graphfield.rewriteAnnotation(unique=True)

			obj.result = xtype
			result = xtype
		else:
			result = self.cache[obj]

		return result

	def countInstances(self):
		count = {}
		for objInfo in self.analysis.objectInfo.itervalues():
			count[objInfo.example] = count.get(objInfo.example, 0)+1
		return count

	def translateObjs(self, objs):
		if objs is None:
			return None
		else:
			return [self.processObject(obj) for obj in objs]

	def translateParam(self, tup):
		param, objs = tup
		xtypes = self.translateObjs(objs)
		if xtypes is not None:
			slotName = self.storeGraph.canonical.localName(self.code, param, None)
			slot = self.storeGraph.root(slotName, self.storeGraph.regionHint)
			slot.initializeTypes(xtypes)
			self.roots.append(slot)
		return xtypes

	def process(self, code, args):
		self.count = self.countInstances()

		self.code  = code
		argobjs = args.map(self.translateParam)

		print "="*60
		print argobjs.selfarg
		for arg in argobjs.args:
			print '\t', arg
		print argobjs.vargs
		print argobjs.kargs
		print

		# Create an entry point
		# The arguments for this entry points are bogus.
		ep = self.shaderprgm.interface.createEntryPoint(code, None, None, None, None, None, None)
		self.shaderprgm.entryPoints.append((ep, argobjs))

	def buildExGraph(self):
		return exclusiongraph.build(self.roots, lambda node: iter(node), lambda node: node.isSlot())


def process(compiler, *codeASTs):
	with compiler.console.scope('analysis'):
		rc = ReadCollector()
		for code in codeASTs:
			rc.process(code)

		analysis = TreeAnalysis(compiler, rc.reads)
		argsList = [(code, analysis.process(code)) for code in codeASTs]

	with compiler.console.scope('resynthesis'):
		resynthesis = TreeResynthesis(compiler, analysis)

		for code, args in argsList:
			resynthesis.process(code, args)

		exgraph = resynthesis.buildExGraph()

	prgm = resynthesis.shaderprgm

	with compiler.console.scope('reanalysis'):
		cpa.evaluateWithImage(compiler, prgm, 3, firstPass=False, clone=True)
		lifetimeanalysis.evaluate(compiler, prgm)


	# The reanalysis will clone the code and create a new copy
	newcode = [ep.code for ep in prgm.interface.entryPoint]

	return resynthesis.shaderprgm, newcode, exgraph, analysis.objectInfo
