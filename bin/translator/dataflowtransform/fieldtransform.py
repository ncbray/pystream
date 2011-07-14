# Copyright 2011 Nicholas Bray
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from util.typedispatch import *
import analysis.dataflowIR.traverse
from analysis.dataflowIR import graph
from language.python import ast

from .. import intrinsics

from PADS.UnionFind import UnionFind

class FieldTransformAnalysis(TypeDispatcher):
	def __init__(self, compiler, dataflow, exgraph):
		TypeDispatcher.__init__(self)
		self.compiler = compiler
		self.dataflow = dataflow

		self.compatable = UnionFind()

		self.loads  = []
		self.stores = []

		self.fields = {}

		self.exgraph = exgraph

	def reads(self, args):
		args = [arg.name for arg in args]
		self.compatable.union(*args)

	def modifies(self, args):
		args = [arg.name for arg in args]
		self.compatable.union(*args)

	@dispatch(ast.DirectCall, ast.Allocate, ast.TypeSwitch)
	def visitOpJunk(self, node, g):
		pass

	@dispatch(ast.Load)
	def visitLoad(self, node, g):
		if not intrinsics.isIntrinsicMemoryOp(node):
			reads  = g.annotation.read.flat

			self.reads(reads)
			self.loads.append(g)


	@dispatch(ast.Store)
	def visitStore(self, node, g):
		if not intrinsics.isIntrinsicMemoryOp(node):
			modifies = g.annotation.modify.flat

			self.modifies(modifies)
			self.stores.append(g)

	@dispatch(graph.Entry, graph.Exit, graph.PredicateNode, graph.Gate,
	graph.NullNode, graph.Split, graph.Merge,)
	def visitJunk(self, node):
		pass

	@dispatch(graph.FieldNode,)
	def visitField(self, node):
		name = node.name
		if name not in self.fields: self.fields[name] = set()
		self.fields[name].add(node.canonical())

	@dispatch(graph.LocalNode, graph.ExistingNode,)
	def visitSlot(self, node):
		pass

	@dispatch(graph.GenericOp)
	def visitOp(self, node):
		self(node.op, node)

	def dumpSlotInfo(self, slot):
		print id(slot)
		print slot
		print "object:", id(slot.object)
		print "region:", id(slot.region)
		print "group: ", slot.region.group

		print self.exgraph.exInfo.get(slot)
		print

	def processGroup(self, group):
		final = True
		preexisting = True
		unique = True


		for objfield in group:
			object = objfield.object
			field  = objfield.slotName

			preexisting &= object.annotation.preexisting
			unique &= object.annotation.unique
			final &= object.annotation.final

		exclusive = self.exgraph.mutuallyExclusive(*group)


		# TODO non-interfering objects?
		if unique and exclusive:
			#print "+", group
			self.transform(group)
		else:
			pass #print "-", group

		if len(group) > 1 and False:
			print "ex?", exclusive
			print
			print
			for objfield in group:
				self.dumpSlotInfo(objfield)
			print
			print "="*20
			print

			for k, v in self.exgraph.exInfo.iteritems():
				if k.isSlot():
					self.dumpSlotInfo(k)

			print

	def makeLocalForGroup(self, group):
		# Make up a name, based on an arbitrary field
		field = group[0].slotName
		name = field.name.pyobj

		if field.type == 'Attribute':
			descriptor = self.compiler.slots.reverse[name]
			originalName = descriptor.__name__
		elif field.type == 'Array':
			originalName = 'array_%d' % name
		elif field.type == 'LowLevel':
			originalName = name

		else:
			assert False, field

		return ast.Local(originalName)

	def getRemap(self, node):
		node = node.canonical()

		if node not in self.remap:
			# TODO chase through merges and gates
			assert False, node.defn

		return self.remap[node]

	def transformEntry(self, group):
		lcl = self.makeLocalForGroup(group)

		hyperblock = self.dataflow.entry.hyperblock
		g = graph.LocalNode(hyperblock, [lcl])

		entry = self.dataflow.entry
		inEntry = False

		for slot in group:
			node = entry.modifies.get(slot)
			if node is not None:
				entry.removeEntry(slot, node)
				self.remap[node] = g
				inEntry = True

		if inEntry:
			self.dataflow.entry.addEntry(lcl, g)

		return lcl

	def transformStores(self, group):
		for store in self.stores:
			sample = tuple(store.annotation.modify.flat)[0].name
			if sample in group:
				value = store.localReads[store.op.value]
				sg = value.canonical()

				for mod in store.heapModifies.itervalues():
					self.remap[mod.canonical()] = sg

				store.destroy()

	def transformLoads(self, group):
		for load in self.loads:
			sample = tuple(load.annotation.read.flat)[0].name
			if sample in group:
				originalSlot = load.heapReads[sample]
				remapped = self.getRemap(originalSlot)

				load.localModifies[0].redirect(remapped)

				load.destroy()

	def transformExit(self, group, lcl):
		exit = self.dataflow.exit
		inExit = False
		g = None

		for slot in group:
			node = exit.reads.get(slot)
			if node is not None:
				exit.removeExit(slot, node)
				g = self.getRemap(node)
				inExit = True

		if inExit:
			self.dataflow.exit.addExit(lcl, g)


	def transform(self, group):
		self.remap = {}

		# Transform definitions
		lcl = self.transformEntry(group)
		self.transformStores(group)

		# Transform uses
		self.transformLoads(group)
		self.transformExit(group, lcl)

		# TODO transfer annotations?



	def postProcess(self):
		groups = {}
		for obj, group in self.compatable.parents.iteritems():
			if group not in groups:
				groups[group] = [obj]
			else:
				groups[group].append(obj)

		print
		print "GROUPS"
		for group in groups.itervalues():
			self.processGroup(group)

	def process(self):
		# Analyze
		analysis.dataflowIR.traverse.dfs(self.dataflow, self)

		self.postProcess()


def process(compiler, dataflow, exgraph):
	fta = FieldTransformAnalysis(compiler, dataflow, exgraph)
	fta.process()
