from util.typedispatch import *
from language.python import ast
from .. import intrinsics
from PADS.UnionFind import UnionFind

from optimization import rewrite, simplify

from . import common

class FieldTransformAnalysis(TypeDispatcher):
	def __init__(self, compiler, prgm, code, exgraph):
		TypeDispatcher.__init__(self)
		self.compiler = compiler
		self.prgm = prgm
		self.code = code

		self.compatable = UnionFind()

		self.loads  = []
		self.stores = []

		self.fields = {}

		self.exgraph = exgraph

	def reads(self, args):
		self.compatable.union(*args)

	def modifies(self, args):
		self.compatable.union(*args)

	@dispatch(ast.leafTypes, ast.Local, ast.Existing, ast.DoNotCare, ast.CodeParameters)
	def visitLeaf(self, node, stmt=None):
		pass

	@dispatch(ast.Suite, ast.TypeSwitch, ast.TypeSwitchCase)
	def visitOK(self, node):
		node.visitChildren(self)

	@dispatch(ast.Assign, ast.Discard)
	def visitAssign(self, node):
		self(node.expr, node)

	@dispatch(ast.Return)
	def visitStatement(self, node):
		pass

	@dispatch(ast.Allocate)
	def visitAllocate(self, node, stmt):
		print node.annotation.allocates.merged


	@dispatch(ast.DirectCall)
	def visitOp(self, node, stmt):
		pass

	@dispatch(ast.Load)
	def visitLoad(self, node, stmt):
		if not intrinsics.isIntrinsicMemoryOp(node):
			reads  = node.annotation.reads.merged

			self.reads(reads)
			self.loads.append(node)


	@dispatch(ast.Store)
	def visitStore(self, node):
		if not intrinsics.isIntrinsicMemoryOp(node):
			modifies  = node.annotation.modifies.merged

			self.modifies(modifies)
			self.stores.append(node)

	### Post processing ###

	def transform(self, name, group):
		lcl = common.localForFieldSlot(self.compiler, self.code, name, group)

		for field in group:
			self.remap[field] = lcl

		isLoaded = False

		for load in self.loadLUT.get(name, ()):
			self.rewrites[load] = lcl
			isLoaded = True

		storeCount = 0
		for store in self.storeLUT.get(name, ()):
			self.rewrites[store] = ast.Assign(store.value, [lcl])
			storeCount += 1

		assert storeCount == 0 or storeCount == 1 and not isLoaded, "Field transform broke SSA form"

	def processGroup(self, name, group):
		unique = True

		for objfield in group:
			# The field is only unique if the object containing it is unique and
			# the field is not a "slop" field (e.g. list[-1])
			unique &= objfield.annotation.unique

		exclusive = self.exgraph.mutuallyExclusive(*group)

		if unique and exclusive:
			print "+", group
			self.transform(name, group)
		else:
			print "-", group
			print unique, exclusive
			print [objfield.object.annotation.unique for objfield in group]
			print


	def fieldGroups(self):
		groups = {}
		for obj, group in self.compatable.parents.iteritems():
			if group not in groups:
				groups[group] = [obj]
			else:
				groups[group].append(obj)
		return groups

	def loadGroups(self):
		loads  = {}
		for load in self.loads:
			example = load.annotation.reads.merged[0]
			group = self.compatable[example]

			if group not in loads:
				loads[group] = [load]
			else:
				loads[group].append(load)
		return loads

	def storeGroups(self):
		stores = {}
		for store in self.stores:
			example = store.annotation.modifies.merged[0]
			group = self.compatable[example]

			if group not in stores:
				stores[group] = [store]
			else:
				stores[group].append(store)

		return stores

	def postProcess(self):
		groups = self.fieldGroups()
		self.loadLUT  = self.loadGroups()
		self.storeLUT = self.storeGroups()
		self.rewrites = {}
		self.remap = {}

		print
		print "GROUPS"
		for name, group in groups.iteritems():
			self.processGroup(name, group)

		# TODO rewrite, SSA, then simplify
		# TODO can we simplify?  The field locals would be eliminated
		# without some sort of anchor.
		rewrite.rewrite(self.compiler, self.code, self.rewrites)

	def process(self):
		self.code.visitChildrenForced(self)
		self.postProcess()


def process(compiler, context):
	prgm = context.prgm
	code = context.code
	exgraph = context.exgraph
	fta = FieldTransformAnalysis(compiler, prgm, code, exgraph)
	fta.process()

	context.shaderdesc.fields = fta.fields

	simplify.evaluateCode(compiler, prgm, code, outputAnchors=context.shaderdesc.outputs.collectUsed())
