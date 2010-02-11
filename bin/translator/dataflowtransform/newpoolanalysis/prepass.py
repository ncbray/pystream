from util.typedispatch import *
from language.python import ast

from . import model

from ... import intrinsics

import collections
from PADS.UnionFind import UnionFind


class UniformInterfaceBuilder(object):
	def __init__(self, compiler, analysis):
		self.compiler = compiler
		self.analysis = analysis

		self.references = {}

		self.renamer = model.Renamer()


	def getSlotRefs(self, slot):
		if isinstance(slot, ast.IOName):
			refs = self.analysis.ioRefs[slot]
		else:
			refs = slot
		return refs

	def getReference(self, slot):
		group = self.analysis.compatible[slot]

		if group not in self.references:
			refInfo = model.ReferenceInfo()
			self.references[group] = refInfo
		else:
			refInfo = self.references[group]

		refInfo.addSlot(slot)

		refs = self.getSlotRefs(slot)

		for ref in refs:
			refInfo.addRef(ref)

		# TODO fields?

		return refInfo

	def nameFromField(self, refInfo, slot):
		if isinstance(slot, ast.Local):
			name = slot.name
			if name is None:
				name = 'bogus'
		elif isinstance(slot, ast.IOName):
			name = 'io'
		else:
			desc = self.compiler.slots.reverse[slot.slotName.name.pyobj]
			name = desc.__name__

		if refInfo.mode is model.UNIFORM:
			return "uni_%s" % (name,)
		elif refInfo.mode is model.INPUT:
			return "inp_%s" % (name,)
		elif refInfo.mode is model.OUTPUT:
			return "out_%s" % (name,)
		else:
			assert False, refInfo.mode

	def process(self):
		ioinfo = self.analysis.ioinfo

		print "uniform fields"
		for field in self.analysis.inputFields:
			if field in ioinfo.uniforms:
				ref = self.getReference(field)
				ref.mode = model.UNIFORM


		# TODO indirect input loads?

		print "inputs"
		for inp in self.analysis.liveInputs:
			if inp in ioinfo.uniforms: continue

			print "inp", inp
			print self.analysis.ioRefs[inp]

			ref = self.getReference(inp)
			ref.mode = model.INPUT

		print

		print "outputs"
		for outp in self.analysis.ioinfo.outputs:
			print outp, ioinfo.same.get(outp), ioinfo.specialOutputs.get(outp)

			ref = self.getReference(outp)
			ref.mode = model.OUTPUT
		print

		outs = []

		for group, refInfo in self.references.iteritems():
			if refInfo.mode is model.OUTPUT:
				# Defer, until the inputs are named.
				outs.append((group, refInfo))
			else:
				refInfo.postProcess()
				name = self.nameFromField(refInfo, group)
				refInfo.name = name

				for sub in refInfo.subpools():
					sub.setBaseName(name, self.renamer)

		for group, refInfo in outs:
			refInfo.postProcess()
			if group in ioinfo.same:
				other = self.getReference(ioinfo.same[group])
				refInfo.copyNames(other)
			elif group in ioinfo.specialOutputs:
				name = ioinfo.specialOutputs[group]
				refInfo.setSpecialName(name)
			else:
				name = self.nameFromField(refInfo, group)
				refInfo.setName(name, self.renamer)



		for group, refInfo in self.references.iteritems():
			print refInfo.name, refInfo.mode
			for sub in refInfo.subpools():
				print '\t', sub.name
		print

		return self.references

class PoolAnalysisInfoCollector(TypeDispatcher):
	def __init__(self, compiler, exgraph, ioinfo):
		self.compiler = compiler
		self.exgraph = exgraph
		self.ioinfo  = ioinfo

		self.compatible = UnionFind()

		self.samplers   = UnionFind()

		self.readFields = set()
		self.modifiedFields = set()

		self.liveInputs  = set()
		self.liveOutputs = set()

		self.ioRefs = {}

		self.inputFields = set()

		self.locals = set()

		self.holdingCount = collections.defaultdict(lambda: 0)

		self.typeIDs = {}
		self.typeUID = 0

		self.samplerGroups = {}

	def samplerGroup(self, sampler):
		return self.samplerGroups[self.samplers[sampler]]

	def handleTypes(self, types):
		if len(types) > 1:
			for t in types:
				self.typeIDs[t] = self.typeUID
				self.typeUID += 1

	def reads(self, args):
		for field in args:
			if field not in self.readFields:
				if field in self.ioinfo.uniforms:
					self.inputFields.add(field)

				# Increase the holding count for objects contained in read fields.
				for ref in field:
					self.holdingCount[ref] += 1

		# TODO translate shader names?
		self.compatible.union(*args)
		self.readFields.update(args)

	def modifies(self, args):
		# TODO translate shader names?
		self.compatible.union(*args)
		self.modifiedFields.update(args)

	@dispatch(ast.Local)
	def visitLocal(self, node):
		if node not in self.locals:
			self.locals.add(node)

			pools = collections.defaultdict(list)
			for ref in node.annotation.references.merged:
				self.holdingCount[ref] += 1 # NOTE this overestimates shared objects, as they are held by multiple shaders.
				pt = ref.xtype.obj.pythonType()
				pools[pt].append(ref)

			for pt, group in pools.iteritems():
				if pt in intrinsics.samplerTypes:
					self.samplers.union(*group)

			self.handleTypes(pools.keys())

	@dispatch(ast.leafTypes, ast.Code, ast.CodeParameters, ast.Existing, ast.DoNotCare)
	def visitLeafs(self, node):
		pass

	@dispatch(ast.DirectCall, ast.Call, ast.Allocate, ast.Discard, ast.Assign, ast.Return)
	def visitOp(self, node):
		node.visitChildren(self)

	@dispatch(ast.Load)
	def visitLoad(self, node):
		self.reads(node.annotation.reads.merged)
		node.visitChildren(self)

	@dispatch(ast.Store)
	def visitStore(self, node):
		self.modifies(node.annotation.modifies.merged)
		node.visitChildren(self)

	@dispatch(ast.InputBlock)
	def visitInputBlock(self, node):
		for input in node.inputs:
			self.liveInputs.add(input.src)
			self.ioRefs[input.src] = input.lcl.annotation.references.merged

	@dispatch(ast.OutputBlock)
	def visitOutputBlock(self, node):
		for output in node.outputs:
			self.liveOutputs.add(output.dst)
			self.ioRefs[output.dst] = output.expr.annotation.references.merged

	@dispatch(ast.Suite, ast.Switch, ast.Condition, ast.While,
			ast.TypeSwitch, ast.TypeSwitchCase)
	def visitOK(self, node):
		node.visitChildren(self)


	def analyzeCode(self, code):
		code.visitChildrenForced(self)


	def postProcess(self):
		# Reconstruct field transform info from ioinfo structure.
		groups = collections.defaultdict(list)

		for field, ioname in self.ioinfo.fieldTrans.iteritems():
			otherio = self.ioinfo.same[ioname]

			if ioname in self.liveInputs or otherio in self.liveInputs:
				groups[ioname].append(field)
				self.inputFields.add(field)
				#print field, ioname, otherio

		self.merged = UnionFind()
		for group in groups.itervalues():
			self.merged.union(*group)
			# TODO only live fields are "compatible"?
			self.compatible.union(*group)

		if False:
			print "Compatible fields"
			for name, group in model.reindexUnionFind(self.compatible).iteritems():
				print name
				for field in group:
					print '\t', field
			print

			print "Merged fields"
			for name, group in model.reindexUnionFind(self.merged).iteritems():
				if len(group) > 1:
					print name
					for field in group:
						print '\t', field
			print

			print "Holding"
			for name, count in self.holdingCount.iteritems():
				print name, count
			print


		# Build sampler groups
		uid = 0
		for name, group in model.reindexUnionFind(self.samplers).iteritems():
			sg = model.SamplerGroup(name, group, uid)
			self.samplerGroups[name] = sg
			uid += 1


		self.volatileFields = set()
		self.volatileIntrinsics = set()

		print "Volatile"
		for field in self.modifiedFields:
			obj = field.object
			if self.holdingCount[obj] > 1:
				if intrinsics.isIntrinsicSlot(field):
					print "obj", obj
					self.volatileIntrinsics.add(obj)
				else:
					print "field", field
					self.volatileFields.add(self.compatible[field])
		print

		uib = UniformInterfaceBuilder(self.compiler, self)
		self.ioRefInfo = uib.process()
		return self


def process(compiler, prgm, exgraph, ioinfo, contexts):
	paic = PoolAnalysisInfoCollector(compiler, exgraph, ioinfo)

	for context in contexts:
		code = context.code
		print code
		paic.analyzeCode(code)

	return paic.postProcess()
