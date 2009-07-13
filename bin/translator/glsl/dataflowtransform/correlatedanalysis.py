from util.typedispatch import *
from language.python import ast
from analysis.dataflowIR import graph
from analysis.fsdf import canonicaltree

import itertools

import analysis.dataflowIR.ordering

from analysis.storegraph import storegraph

from . import imagebuilder

# For dumping
from util.xmloutput import XMLOutput
import sys
import os.path

class GenericOpFunction(TypeDispatcher):
	def __init__(self, manager):
		self.func = canonicaltree.TreeFunction(manager, self.concrete, True)

	def init(self, analysis, g):
		self.inputlut   = {} # maps (name, index) -> index in inputs
		self.inputs     = []
		self.inputNodes = []

		self.outputlut   = {} # maps (name, index) -> index in outputs
		self.outputs     = []
		self.outputNodes = []

		self.g         = g
		self.op        = g.op
		self.analysis  = analysis
		self.canonical = analysis.compiler.storeGraph.canonical

	def registerInput(self, analysis, name, node):
		if (name, 0) not in self.inputlut:
			for index in range(self.analysis.numValues(node)):
				self.inputlut[(name, index)] = len(self.inputs)
				self.inputs.append(analysis.getValue(node, index))
				self.inputNodes.append((node, index))

	def registerOutput(self, analysis, name, node):
		if (name, 0) not in self.outputlut:
			for index in range(self.analysis.numValues(node)):
				self.outputlut[name, index] = len(self.outputs)
				self.outputs.append((node, index)) # TODO?
				self.outputNodes.append((node, index))

	# Gets the concrete input
	def get(self, name, index):
		assert not isinstance(name, graph.SlotNode), name
		assert isinstance(index, int), index
		return self.args[self.inputlut[name, index]]

	# Sets the concrete output.
	def set(self, name, index, value, weak=False):
		assert not isinstance(name, graph.SlotNode), name
		assert isinstance(index, int), index
		assert isinstance(value, frozenset), value

		for ref in value:
			if isinstance(ref, bool): continue
			obj, objindex = ref
			assert isinstance(obj, storegraph.ObjectNode), obj
			assert isinstance(objindex, int), objindex

		outindex = self.outputlut[name, index]
		node, nodeindex = self.outputNodes[outindex]

		if weak or not self.analysis.isUnique(node, nodeindex):
			# Merge with the existing value.
			current = self.results[outindex]
			value = current.union(value)

		self.results[outindex] = value

	def copy(self, name, node):
		for i in range(self.analysis.numValues(node)):
			self.set(name, i, self.get(name, i))

	def fresh(self, ref):
		return self.analysis.allocateFreshIndex.get(ref, 0)

	@dispatch(ast.DirectCall)
	def handleDirectCall(self, node):
		# HACK currently, these will only be primitive operations, so fake it.
		# Also relies on primitive types being immutable.
		for name, index in self.outputlut.iterkeys():
			if isinstance(name, ast.Local):
				values = frozenset([(ref, self.fresh(ref)) for ref in name.annotation.references.merged])
				self.set(name, index, values)
			else:
				values = frozenset([(ref, self.fresh(ref)) for ref in name])
				self.set(name, index, values)


	@dispatch(ast.Allocate)
	def handleAllocate(self, node):
		# TODO more precise?
		# Return value

		allocated = [(ref, self.analysis.allocateFreshIndex[ref]) for ref in node.annotation.allocates.merged]
		self.set(self.g.localModifies[0].names[0], 0, frozenset(allocated))

	@dispatch(ast.Load)
	def handleLoad(self, node):
		expr      = self.get(node.expr, 0)
		fieldtype = self.op.fieldtype
		name      = self.get(node.name, 0)

		result = set()
		for (expr, ei), (name, ni) in itertools.product(expr, name):
			field = self.canonical.fieldName(fieldtype, name.xtype.obj)
			slot  = expr.knownField(field)
			result.update(self.get(slot, ei))

		# Return value
		self.set(self.g.localModifies[0].names[0], 0, frozenset(result))

	@dispatch(ast.Store)
	def handleStore(self, node):
		expr      = self.get(node.expr, 0)
		fieldtype = self.op.fieldtype
		name      = self.get(node.name, 0)
		value     = self.get(node.value, 0)


		ambiguous = len(expr)*len(name) > 1

		for (expr, ei), (name, ni) in itertools.product(expr, name):
			field = self.canonical.fieldName(fieldtype, name.xtype.obj)
			slot  = expr.knownField(field)

			# TODO non-ambiguous unique?
			self.set(slot, ei, value, weak=ambiguous)

		# TODO uncovered fields?

	@dispatch(ast.TypeSwitch)
	def handleTypeSwitch(self, node):
		# TODO need to inject new correlation?

		conditional = self.get(node.conditional, 0)
		types = set([ref.xtype.obj.type for ref, ri in conditional])

		for i, case in enumerate(node.cases):
			casetypes = set([e.object for e in case.types])

			# Calculate the predicate
			t = not types.isdisjoint(casetypes)
			f = not casetypes.issuperset(types)

			if t:
				if f:
					# Uncertain if the branch will be taken
					self.set(i, 0, frozenset((True, False)))
				else:
					# This branch must be taken
					self.set(i, 0, frozenset((True,)))
			elif f:
				# The branch will not be taken.
				self.set(i, 0, frozenset((False,)))

			# Calculate the filtered value
			if case.expr is not None:
				filtered = frozenset([ref for ref in conditional if ref[0].xtype.obj.type in casetypes])
				self.set(case.expr, 0, filtered)

	# This function is called for all combinations of leafs
	def concrete(self, *args):
		# Init concrete inputs
		self.args = args

		# Init concrete outputs
		empty = frozenset()
		self.results = [empty for o in self.outputs]

		# If predicate cannot be true, no point in evaluating?
		if True in self.get('predicate', 0):
			# Copy the psedo reads.
			# If a strong write is performed, it will overwrite this value.
			# If a weak write is performed, it will be merged with this value.
			# If no write is performed, the copy will pass the value through.
			for name, node in self.g.heapPsedoReads.iteritems():
				assert name in self.g.heapModifies, name
				self.copy(name, node)

			# evaluate this spesific op
			self(self.op)

		# Note that if the predicate cannot be true, the results are undefined.
		return tuple(self.results)

	def dispatch(self, analysis, g):
		self.init(analysis, g)

		# Pack the inputs
		self.registerInput(analysis, 'predicate', g.predicate)

		for name, node in g.localReads.iteritems():
			self.registerInput(analysis, name, node)
		for name, node in g.heapReads.iteritems():
			self.registerInput(analysis, name, node)
		for name, node in g.heapPsedoReads.iteritems():
			self.registerInput(analysis, name, node)

		# Declare the outputs
		for node in g.localModifies:
			self.registerOutput(analysis, node.names[0], node)
		for name, node in g.heapModifies.iteritems():
			self.registerOutput(analysis, name, node)
		for i, node in enumerate(g.predicates):
			self.registerOutput(analysis, i, node)

		# Evaluate
		result = self.func(*self.inputs)

		# Unpack the outputs
		for (node, index), value in zip(self.outputNodes, result):
			analysis.setValue(node, index, value)

		# Type switch fixup
		# TODO functions can't inject new correlations, so we must fixup?
		if isinstance(g.op, ast.TypeSwitch):
			correlation = analysis.cond.condition(g.op, range(len(g.op.cases)))

			for mask, pnode, enode in zip(correlation.mask.itervalues(), g.predicates, g.localModifies):
				analysis.maskSetValue(pnode, 0, mask)
				if enode is not None: analysis.maskSetValue(enode, 0, mask)


class DataflowIOAnalysis(TypeDispatcher):
	def __init__(self, compiler, dataflow, order, name):
		self.compiler = compiler
		self.dataflow = dataflow
		self.order    = order
		self.name     = name

		# Indexed slot
		self._values    = {}
		self.slotUnique = {}

		# Indexed object
		self.objUnique  = {}

		# Unindexed object
		self.objCount   = {} # How many different objects are there, for a given name?

		self.pathObjIndex       = {}
		self.allocateFreshIndex = {}
		self.allocateMergeIndex = {}

		self.cond = canonicaltree.ConditionManager()
		self.bool = canonicaltree.BoolManager(self.cond)
		self.set  = canonicaltree.SetManager()

		#self.path = PathManager()

		self.opfunc = GenericOpFunction(self.set)

		self.dead = self.set.leaf((False,))

	@dispatch(graph.Entry)
	def processEntry(self, node):
		pass

	@dispatch(graph.Exit)
	def processExit(self, node):
		pass

	@dispatch(graph.Split)
	def processSplit(self, node):
		for i in range(self.numValues(node.read)):
			value = self.getValue(node.read, i)
			for m in node.modifies:
				self.setValue(m, i, value)

	@dispatch(graph.Gate)
	def processGate(self, node):
		pred = self.getValue(node.predicate, 0)

		for i in range(self.numValues(node.read)):
			value = self.getValue(node.read, i)
			value = self.set.ite(pred, value, self.set.empty)
			self.setValue(node.modify, i, value)

	@dispatch(graph.Merge)
	def processMerge(self, node):
		for i in range(self.numValues(node.reads[0])):
			value = self.set.empty
			for r in node.reads:
				input = self.getValue(r, i)
				value = self.set.union(value, input)
			self.setValue(node.modify, i, value)

	@dispatch(graph.GenericOp)
	def processGenericOp(self, node):
		self.opfunc.dispatch(self, node)

	def setValue(self, node, index, value):
		assert isinstance(node, graph.SlotNode), type(node)
		assert isinstance(value, canonicaltree.AbstractNode), type(value)
		self._values[(node, index)] = value

	def getValue(self, node, index):
		assert isinstance(node, graph.SlotNode), type(node)
		return self._values.get((node, index), self.set.empty)

	def isUnique(self, node, index):
		assert isinstance(node, graph.SlotNode), type(node)
		if node.mustBeUnique():
			result = True
		else:
			obj       = node.name.object
			objUnique = self.objUnique.get((obj, index), False)
			result = self.slotUnique.get(node, objUnique)

		return result

	def numValues(self, node):
		assert isinstance(node, graph.SlotNode), type(node)

		if node.mustBeUnique():
			return 1
		else:
			assert isinstance(node, graph.FieldNode), node
			count = self.getCount(node.name.object)

			# We forgot to initialize an object?
			assert count != 0, node

			return count

	def maskSetValue(self, node, index, mask):
		value  = self.getValue(node, index)
		masked = self.set.ite(mask, value, self.set.empty)
		self.setValue(node, index, masked)

	def getCount(self, obj):
		assert isinstance(obj, storegraph.ObjectNode), obj
		return self.objCount.get(obj, 0)

	def incrementCount(self, obj, unique=False):
		current = self.getCount(obj)
		self.objCount[obj] = current + 1
		self.objUnique[(obj, current)] = unique
		return current

	def initLocal(self, lcl, node):
		leaf = self.set.leaf([(obj, 0) for obj in lcl.annotation.references.merged])
		self.setValue(node, 0, leaf)

	def initField(self, field, index, node):
		refs = [(ref, 0) for ref in field]
		leaf = self.set.leaf(refs)
		self.setValue(node, index, leaf)

	def process(self):
		# Bind null value
		self.setValue(self.dataflow.null, 0, self.set.leaf(()))


		storeGraph = self.compiler.storeGraph
		# Bind existing values
		for obj, e in self.dataflow.existing.iteritems():
			ref = e.ref
			leaf = self.set.leaf(((ref, 0),))
			self.setValue(e, 0, leaf)

		imagebuilder.build(self)

		# Initalize the slots
		for name, node in self.dataflow.entry.modifies.iteritems():
			if name == '*':
				# Entry predicate
				self.setValue(node, 0, self.set.leaf((True,)))
			elif isinstance(node, graph.LocalNode):
				# Local slot
				pass #self.initLocal(name, node)
			elif isinstance(node, graph.FieldNode):
				# Field slot
				pass #self.initField(name, 0, node)
			else:
				assert False


		if True:
			# Analyize
			for op in self.order:
				self(op)

		if True:
			with self.compiler.console.scope('debug dump'):
				self.debugDump()

	def dumpValues(self, out, node):
		with out.scope('ul'):
			for i in range(self.numValues(node)):
				with out.scope('li'):
					values = self.getValue(node, i)
					out.write(values)
				out.endl()
		out.endl()

	def dumpNodes(self, out, title, iterable):
		if title:
			with out.scope('h3'):
				out.write(title)
			out.endl()

		with out.scope('ul'):
			for node in iterable:
				with out.scope('li'):
					out.write(node)
					self.dumpValues(out, node)
				out.endl()
		out.endl()


	def debugDump(self):
		# Dump output
		name = self.name
		filename = name + ".html"
		fullname = os.path.join('summaries\\dataflow', filename)

		f = open(fullname, 'w')
		out = XMLOutput(f)

		with out.scope('html'):
			with out.scope('head'):
				with out.scope('title'):
					out.write(name)
			out.endl()

			with out.scope('body'):
				for op in self.order:
					out.tag('hr')
					out.endl()

					out.write(op)
					out.endl()

					self.dumpNodes(out, 'Inputs', op.reverse())
					self.dumpNodes(out, 'Outputs', op.forward())
		out.endl()

def evaluateDataflow(compiler, dataflow, name):
	order = analysis.dataflowIR.ordering.evaluateDataflow(dataflow)

	dioa = DataflowIOAnalysis(compiler, dataflow, order, name)
	dioa.process()
