from util.typedispatch import *
from language.python import ast
from .. import intrinsics
from PADS.UnionFind import UnionFind

from optimization import rewrite, simplify

from . import common

from analysis.cfg import ssatransform

class FieldTransformAnalysis(TypeDispatcher):
	def __init__(self, compiler, prgm, exgraph):
		TypeDispatcher.__init__(self)
		self.compiler = compiler
		self.prgm = prgm

		self.compatable = UnionFind()

		self.loads  = []
		self.stores = []

		self.fields = {}

		self.exgraph = exgraph

		self.ssaBroken = False

	def reads(self, args):
		self.compatable.union(*args)

	def modifies(self, args):
		self.compatable.union(*args)

	@dispatch(ast.leafTypes, ast.Local, ast.Existing, ast.DoNotCare, ast.CodeParameters, ast.OutputBlock)
	def visitLeaf(self, node, stmt=None):
		pass

	@dispatch(ast.Suite, ast.Switch, ast.Condition, ast.TypeSwitch, ast.TypeSwitchCase, ast.While)
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
		pass

	@dispatch(ast.DirectCall)
	def visitOp(self, node, stmt):
		pass

	@dispatch(ast.Load)
	def visitLoad(self, node, stmt):
		if not intrinsics.isIntrinsicMemoryOp(node):
			reads  = node.annotation.reads.merged

			self.reads(reads)
			self.loads.append((self.code, node))


	@dispatch(ast.Store)
	def visitStore(self, node):
		if not intrinsics.isIntrinsicMemoryOp(node):
			modifies  = node.annotation.modifies.merged

			self.modifies(modifies)
			self.stores.append((self.code, node))

	### Post processing ###

	def transform(self, code, name, group):
		lcl = common.localForFieldSlot(self.compiler, code, name, group)

		ioname = ast.IOName(None)

		self.header.append(ast.Input(ioname, lcl))

		for field in group:
			self.remap[field] = lcl, ioname


	def generateRewrites(self, code, name, group):
		lcl, ioname = self.remap[name]

		for field in group:
			self.fields[field] = ioname

		isLoaded = False

		for load in self.loadLUT.get((code, name), ()):
			self.rewrites[load] = lcl
			isLoaded = True

		storeCount = 0
		for store in self.storeLUT.get((code, name), ()):
			self.rewrites[store] = ast.Assign(store.value, [lcl])
			storeCount += 1

		if storeCount > 1 or storeCount == 1 and isLoaded:
			self.ssaBroken = True


	def processGroup(self, code, name, group):
		self.transform(code, name, group)
		self.generateRewrites(code, name, group)


	def filterGroups(self, groups):
		filtered = {}

		print
		print "GROUPS"

		for name, group in groups.iteritems():
			unique = True

			for objfield in group:
				# The field is only unique if the object containing it is unique and
				# the field is not a "slop" field (e.g. list[-1])
				unique &= objfield.annotation.unique

			exclusive = self.exgraph.mutuallyExclusive(*group)

			if unique and exclusive:
				print "+", group
				filtered[name] = group
			else:
				print "-", group
				print unique, exclusive
				print [objfield.object.annotation.unique for objfield in group]
				print

		return filtered

	def fieldGroups(self):
		groups = {}
		for obj, group in self.compatable.parents.iteritems():
			if group not in groups:
				groups[group] = [obj]
			else:
				groups[group].append(obj)

		return self.filterGroups(groups)

	def loadGroups(self):
		loads  = {}
		for code, load in self.loads:
			example = load.annotation.reads.merged[0]
			group = self.compatable[example]

			key = (code, group)
			if key not in loads:
				loads[key] = [load]
			else:
				loads[key].append(load)
		return loads

	def storeGroups(self):
		stores = {}
		for code, store in self.stores:
			example = store.annotation.modifies.merged[0]
			group = self.compatable[example]

			key = (code, group)
			if key not in stores:
				stores[key] = [store]
			else:
				stores[key].append(store)

		return stores

	def postProcess(self):
		self.groups = self.fieldGroups()
		self.loadLUT  = self.loadGroups()
		self.storeLUT = self.storeGroups()

	def postProcessCode(self, code):
		self.rewrites = {}
		self.remap = {}
		self.fields = {}
		self.header = []

		for name, group in self.groups.iteritems():
			self.processGroup(code, name, group)

		rewrite.rewrite(self.compiler, code, self.rewrites)

		code.ast = ast.Suite([ast.InputBlock(self.header), code.ast])

		# TODO SSA
		assert not self.ssaBroken
		simplify.evaluateCode(self.compiler, self.prgm, code)


	def process(self, code):
		self.code = code
		code.visitChildrenForced(self)

def process(compiler, prgm, exgraph, *contexts):
	fta = FieldTransformAnalysis(compiler, prgm, exgraph)

	for context in contexts:
		fta.process(context.code)

	fta.postProcess()

	for context in contexts:
		fta.postProcessCode(context.code)
		context.shaderdesc.fields = fta.fields
