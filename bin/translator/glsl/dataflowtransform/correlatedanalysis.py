from util.typedispatch import *
from language.python import ast
from analysis.dataflowIR import graph
from analysis.fsdf import canonicaltree

import itertools
import collections

import analysis.dataflowIR.ordering

from analysis.storegraph import storegraph

from . import imagebuilder
from . import flattendataflow

# For dumping
from util.io.xmloutput import XMLOutput

from util.application.async import *
from util.io import filesystem

class GenericOpFunction(TypeDispatcher):
	def __init__(self, manager):
		self.func = canonicaltree.TreeFunction(manager, self.concrete, True)

	def init(self, analysis, g):
		self.numInputs   = 0
		self.inputlut    = {} # maps (name, index) -> (position in inputValues, unique
		self.inputValues = []

		self.numOutputs  = 0
		self.outputlut   = {} # maps (name, index) -> position in outputValues
		self.outputs     = [] # list of (node, index, position) to output.

		self.g         = g
		self.op        = g.op
		self.analysis  = analysis
		self.canonical = analysis.compiler.storeGraph.canonical

		# The positions for returning correlated RMA information.
		self.readPosition     = self.allocateOutput()
		self.modifyPosition   = self.allocateOutput()
		self.allocatePosition = self.allocateOutput()


	def allocateInput(self):
		temp = self.numInputs
		self.numInputs += 1
		return temp

	def allocateOutput(self):
		temp = self.numOutputs
		self.numOutputs += 1
		return temp

	def registerInput(self, analysis, name, node):
		if (name, 0) not in self.inputlut:
			for index in range(self.analysis.numValues(node)):
				current = self.allocateInput()
				self.inputlut[(name, index)] = (node, current)
				self.inputValues.append(analysis.getValue(node, index))

	def registerOutput(self, analysis, name, node):
		if (name, 0) not in self.outputlut:
			for index in range(self.analysis.numValues(node)):
				current = self.allocateOutput()
				unique  = self.analysis.isUniqueSlot(node, index)
				self.outputlut[name, index] = (node, current, unique)
				self.outputs.append((node, index, current))

	def registerIO(self, analysis, g):
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


	def assertConcreteValue(self, value):
		assert isinstance(value, (frozenset, set)), value
		for ref in value:
			if isinstance(ref, bool): continue
			obj, objindex = ref
			assert isinstance(obj, storegraph.ObjectNode), obj
			assert isinstance(objindex, int), objindex

	def logRead(self, node, index):
		if node.isField():
			self.results[self.readPosition]   |= set([(node.canonical(), index)])

	def logModify(self, node, index):
		if node.isField():
			self.results[self.modifyPosition] |= set([(node.canonical(), index)])

	def logAllocate(self, obj, index):
		self.results[self.allocatePosition] |= set([(obj, index)])


	# Gets the concrete input
	def get(self, name, index):
		assert not isinstance(name, graph.SlotNode), name
		assert isinstance(index, int), index

		node, pos = self.inputlut[name, index]
		self.logRead(node, index)
		return self.args[pos]

	# Sets the concrete output.
	def set(self, name, index, value, weak=False):
		assert not isinstance(name, graph.SlotNode), name
		assert isinstance(index, int), index
		self.assertConcreteValue(value)


		node, pos, unique = self.outputlut[name, index]

		self.logModify(node, index)

		if weak or not unique:
			# Merge with the existing value.
			value = self.results[pos].union(value)

		self.results[pos] = value

	# Used for initializing the results with pass-through values
	def copy(self, name, node):
		for index in range(self.analysis.numValues(node)):
			# Don't use get/set as it will log as a read/write?
			_inode, inputpos = self.inputlut[name, index]
			_onode, outpos, _unique = self.outputlut[name, index]
			self.results[outpos] = self.args[inputpos]

	def fresh(self, ref):
		assert ref.isObjectContext(), ref

		# The only case that ref will not be in the dictionary is when
		# the ref is a constant, and in this case the index will be zero.
		return self.analysis.allocateFreshIndex.get(ref, 0)

	@dispatch(ast.DirectCall)
	def handleDirectCall(self, node):
		# HACK currently, these will only be primitive operations, so fake it.

		# Read all fields from all input objects
		for name, index in self.inputlut.iterkeys():
			if isinstance(name, ast.Local):
				# It's an argument, check all possible objects
				values = self.get(name, index)
				for obj, index in values:
					# Check all possible fields
					for slot in obj.slots.itervalues():
						# If it's an input, read it
						key = (slot, index)
						if key in self.inputlut:
							self.get(slot, index)
					
			
		# Write all fields on output objects
		for name, index in self.outputlut.iterkeys():
			if isinstance(name, ast.Local):
				values = frozenset([(ref, self.fresh(ref)) for ref in name.annotation.references.merged])
				self.set(name, index, values)
			else:
				# Only set fields of the fresh object.
				if self.fresh(name.object) == index:
					values = frozenset([(ref, self.fresh(ref)) for ref in name])
					self.set(name, index, values)
				else:
					values = ()

			for ref, rindex in values:
				self.logAllocate(ref, rindex)

	@dispatch(ast.Allocate)
	def handleAllocate(self, node):
		# TODO more precise?
		# Return value

		allocated = [(ref, self.analysis.allocateFreshIndex[ref]) for ref in node.annotation.allocates.merged]

		for ref, index in allocated:
			self.logAllocate(ref, index)

		self.set(self.g.localModifies[0].names[0], 0, frozenset(allocated))

	def fieldSlot(self, expr, fieldtype, name):
		field = self.canonical.fieldName(fieldtype, name.xtype.obj)
		return expr.knownField(field)

	@dispatch(ast.Load)
	def handleLoad(self, node):
		expr      = self.get(node.expr, 0)
		fieldtype = self.op.fieldtype
		name      = self.get(node.name, 0)

		result = set()
		for (expr, ei), (name, _ni) in itertools.product(expr, name):
			slot = self.fieldSlot(expr, fieldtype, name)
			result.update(self.get(slot, ei))

		# Output the loaded value
		assert len(self.g.localModifies) == 1
		self.set(self.g.localModifies[0].names[0], 0, result)

	@dispatch(ast.Store)
	def handleStore(self, node):
		expr      = self.get(node.expr, 0)
		fieldtype = self.op.fieldtype
		name      = self.get(node.name, 0)
		value     = self.get(node.value, 0)

		# Are there multiple slots that will be stored to?
		# At runtime, only one of the slots will be updated, therefore
		# it must be analyized as a weak update.
		ambiguous = len(expr)*len(name) > 1

		for (expr, ei), (name, _ni) in itertools.product(expr, name):
			slot = self.fieldSlot(expr, fieldtype, name)
			self.set(slot, ei, value, weak=ambiguous)

	@dispatch(ast.TypeSwitch)
	def handleTypeSwitch(self, node):
		# TODO could we inject the new correlation here, rather than later?  Make the cases a correlated input?

		conditional = self.get(node.conditional, 0)
		types = set([ref.xtype.obj.type for ref, _ri in conditional])

		for i, case in enumerate(node.cases):
			casetypes = set([e.object for e in case.types])

			# Calculate the predicate for this case
			t = not types.isdisjoint(casetypes) # The case may be taken.
			f = not casetypes.issuperset(types) # The case may not be taken.

			# The predicate may be (), (True), (False), or (True, False)
			s = set()
			if t: s.add(True)
			if f: s.add(False)
			self.set(i, 0, s)

			# Calculate the value output for this case.
			if case.expr is not None:
				filtered = frozenset([ref for ref in conditional if ref[0].xtype.obj.type in casetypes])
				self.set(case.expr, 0, filtered)

	# This function is called for all combinations of leafs
	def concrete(self, *args):
		# Init concrete inputs
		self.args = args

		# Init concrete outputs
		empty = frozenset()
		self.results = [empty for _o in range(self.numOutputs)]

		# If predicate cannot be true, no point in evaluating?
		if True in self.get('predicate', 0):
			# Copy the psedo reads.
			# If a strong write is performed, it will overwrite this value.
			# If a weak write is performed, it will be merged with this value.
			# If no write is performed, the copy will pass the value through.
			for name, node in self.g.heapPsedoReads.iteritems():
				assert name in self.g.heapModifies, name
				self.copy(name, node)

			# evaluate this specific op
			self(self.op)

		# Note that if the predicate cannot be true, the results are undefined.
		return tuple(self.results)

	def correlationFixup(self, analysis, g):
		# TODO functions can't inject new correlations, so we must fix it up afterwards?
		
		# Type switch fixup
		if isinstance(g.op, ast.TypeSwitch):
			# Creates a new correlation for the type switch (g.op)
			correlation = analysis.cond.condition(g.op, range(len(g.op.cases)))

			for mask, pnode, enode in zip(correlation.mask.itervalues(), g.predicates, g.localModifies):
				# Mask the predicate
				analysis.maskSetValue(pnode, 0, mask)
				
				# Mask the local, if present
				if enode is not None: analysis.maskSetValue(enode, 0, mask)

	def dispatch(self, analysis, g):
		self.init(analysis, g)
		self.registerIO(analysis, g)

		# Evaluate
		result = self.func(*self.inputValues)

		# Unpack the outputs
		for node, index, position in self.outputs:
			analysis.setValue(node, index, result[position])

		self.correlationFixup(analysis, g)

		analysis.opReads[g]     = result[self.readPosition]
		analysis.opModifies[g]  = result[self.modifyPosition]


		allocates = result[self.allocatePosition]
		analysis.opAllocates[g] = allocates

		# Build existence mask for allocated objects.
		# HACK This seems a little cumbersome, as it traverses the tree multiple times.
		flatAllocates = analysis.set.flatten(allocates)
		for key in flatAllocates:
			leaf = analysis.set.leaf((key,))
			mask = analysis.bool.in_(leaf, allocates)

			obj, index = key
			analysis.accumulateObjectExists(obj, index, mask)

class DataflowIOAnalysis(TypeDispatcher):
	def __init__(self, compiler, dataflow, order):
		self.compiler = compiler
		self.dataflow = dataflow
		self.order    = order

		# Indexed slot
		# (node, index) -> references
		self._values    = {}

		# obj -> # indexes
		self.objCount   = {}

		# The index of various types of objects
		self.pathObjIndex       = {}
		self.allocateFreshIndex = {}
		self.allocateMergeIndex = {}

		# Managers for correlated trees
		self.cond = canonicaltree.ConditionManager()
		self.bool = canonicaltree.BoolManager(self.cond)
		self.set  = canonicaltree.SetManager()

		self.opfunc = GenericOpFunction(self.set)

		# (node, index) -> slot unique?
		# (object unique is necessary but not sufficient)
		self.slotUnique = {}

		# (obj, index) -> unique?
		self.objUnique  = {}

		# A mask that indicates under what conditions the object will be allocated.
		# (obj, index) -> tree(bool)
		self.objectExistanceMask = collections.defaultdict(lambda: self.bool.false)

		# Objects that exist before the shader is executed
		self.objectPreexisting = set()

		self.opReads     = collections.defaultdict(lambda: self.set.empty)
		self.opModifies  = collections.defaultdict(lambda: self.set.empty)
		self.opAllocates = collections.defaultdict(lambda: self.set.empty)


	def accumulateObjectExists(self, obj, index, mask):
		key = (obj, index)
		current = self.objectExistanceMask[key]
		self.objectExistanceMask[key] = self.bool.or_(current, mask)

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

	def isUniqueObject(self, obj, index):
		return self.objUnique.get((obj, index), False)

	def isUniqueSlot(self, node, index):
		assert isinstance(node, graph.SlotNode), type(node)
		if node.mustBeUnique():
			result = True
		else:
			objUnique = self.isUniqueObject(node.name.object, index)
			result    = self.slotUnique.get(node, objUnique)
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

	def objectIsPreexisting(self, obj, index):
		return (obj, index) in self.objectPreexisting

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

		# Bind existing values
		for e in self.dataflow.existing.itervalues():
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

	def opMask(self, op):
		if hasattr(op, 'predicate'):
			p = op.predicate
			mask = self.bool.maybeTrue(self.getValue(p, 0))
		else:
			mask = self.bool.true
		
		return mask

	def dumpMasked(self, out, values, mask):
		values = self.set.simplify(mask, values, self.set.empty)
		out.write(values)

	def dumpValues(self, out, node, mask):
		with out.scope('ul'):
			for i in range(self.numValues(node)):
				with out.scope('li'):
					self.dumpMasked(out, self.getValue(node, i), mask)
				out.endl()
		out.endl()

	def dumpNodes(self, out, title, iterable, mask):
		if title:
			self.dumpTitle(out, title)

		with out.scope('ul'):
			for node in iterable:
				with out.scope('li'):
					out.write(node)
					self.dumpValues(out, node, mask)
				out.endl()
		out.endl()

	def dumpTitle(self, out, title):
		with out.scope('h3'):
			out.write(title)
		out.endl()

	@async_limited(2)
	def debugDump(self, name):
		# Dump output

		directory = 'summaries\\dataflow'

		# Dump information about ops
		f   = filesystem.fileOutput(directory, name+'-ops', 'html')
		out = XMLOutput(f)

		with out.scope('html'):
			with out.scope('head'):
				with out.scope('title'):
					out.write(name)
			out.endl()

			with out.scope('body'):
				for op in self.order:
					if isinstance(op, (graph.Merge, graph.Split)): continue

					out.tag('hr')
					out.endl()

					out.write(op)
					out.endl()

					mask = self.opMask(op)

					if mask is not self.bool.true:
						with out.scope('p'):
							out.write(mask)

					if self.opReads[op] is not self.set.empty:
						self.dumpTitle(out, 'Read')
						self.dumpMasked(out, self.opReads[op], mask)

					if self.opModifies[op] is not self.set.empty:
						self.dumpTitle(out, 'Modify')
						self.dumpMasked(out, self.opModifies[op], mask)

					if self.opAllocates[op] is not self.set.empty:
						self.dumpTitle(out, 'Allocates')
						self.dumpMasked(out, self.opAllocates[op], mask)

					self.dumpNodes(out, 'Inputs', op.reverse(), mask)
					self.dumpNodes(out, 'Outputs', op.forward(), mask)
		out.endl()
		f.close()

		# Dump information about memory
		f   = filesystem.fileOutput(directory, name+'-memory', 'html')
		out = XMLOutput(f)

		with out.scope('html'):
			with out.scope('head'):
				with out.scope('title'):
					out.write(name)
			out.endl()

			with out.scope('body'):
				for key, mask in self.objectExistanceMask.iteritems():
					with out.scope('p'):
						assert isinstance(key, tuple), key
						
						obj, index = key
						
						out.write(obj)
						out.write(' - ')
						out.write(index)
						out.tag('br')
						out.write('preexisting' if self.objectIsPreexisting(obj, index) else 'allocated')
						out.tag('br')
						out.write(mask)

		out.endl()
		f.close()

def evaluateDataflow(compiler, dataflow):
	# Find a linear order to evaluate the dataflow nodes in
	order = analysis.dataflowIR.ordering.evaluateDataflow(dataflow)

	# Do a very flow-sensitive analysis to resolve points-to relations as
	# precisely as possible.
	dioa = DataflowIOAnalysis(compiler, dataflow, order)
	dioa.process()

	# HACK store on dioa
	# TODO do not return dioa, just the dataflow
	dioa.flat = flattendataflow.evaluateDataflow(compiler, dataflow, order, dioa)

	return dioa
