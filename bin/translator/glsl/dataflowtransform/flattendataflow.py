from util.typedispatch import *
from language.python import ast
from analysis.dataflowIR import graph
from analysis.dataflowIR.transform import dce
from analysis.dataflowIR import annotations

from analysis.fsdf import canonicaltree

class DataflowFlattener(TypeDispatcher):
	def __init__(self, compiler, dataflow, order, dioa):
		self.compiler = compiler
		self.dataflow = dataflow
		self.order    = order
		self.dioa     = dioa

		self.objects     = {}
		self.fields      = {}
		self.nodes       = {}

		self.dout = graph.DataflowGraph(self.dataflow.entry.hyperblock)

		self.fieldMapper = canonicaltree.UnaryTreeFunction(self.dioa.set, self._mapFields)
		self.objMapper   = canonicaltree.UnaryTreeFunction(self.dioa.set, self._mapObjects)


	def replacementObject(self, obj, index):
		key = (obj, index)
		if key not in self.objects:
			if self.dioa.getCount(obj) > 1:
				xtype = obj.xtype
				indexedType = self.compiler.storeGraph.canonical.indexedType(xtype)
				replacement = self.compiler.storeGraph.regionHint.object(indexedType)
			else:
				replacement = obj # HACK
			self.translateObjectAnnotations(key, replacement)
			self.objects[key] = replacement
		else:
			replacement = self.objects[key]
		return replacement

	def replacementFieldSlot(self, name, index):
		key = (name, index)
		if key not in self.fields:
			newobj = self.replacementObject(name.object, index)
			newfield = newobj.field(name.slotName, self.compiler.storeGraph.regionHint)
			self.fields[key] = newfield
		else:
			newfield = self.fields[key]
		return newfield

	def iterIndexes(self, node):
		return range(self.dioa.numValues(node))

	def iterFieldIndexes(self, name):
		return range(self.dioa.getCount(name.object))
	
	def connect(self, name, src, dst, index):
		assert isinstance(src, graph.FieldNode), src
		assert isinstance(dst, graph.FieldNode), dst

		srcName, srcNode = self(src, index, name)
		dstName, dstNode = self(dst, index, name)
	
		# Modify the cache
		self.nodes[(dst, index)] = srcNode
	
		dstNode.canonical().redirect(srcNode)
	
	@dispatch(type(None))
	def visitNone(self, node, index, name=None):
		if name is not None:
			return name, None
		else:
			return None

	@dispatch(graph.PredicateNode)
	def visitPredicateNode(self, node, index, name=None):
		node = node.canonical()
		key = (node, index)
		
		if key not in self.nodes:
			result = graph.PredicateNode(node.hyperblock, node.name)
			self.translateSlotAnnotations(key, result)
			self.nodes[key] = result
		else:
			result = self.nodes[key]
		
		if name is not None:
			return name, result
		else:
			return result
		

	@dispatch(graph.FieldNode)
	def visitFieldNode(self, node, index, name=None):
		node = node.canonical()
		key = (node, index)		
		
		if key not in self.nodes:
			assert name is not None
			newfieldslot = self.replacementFieldSlot(name, index)
			result = graph.FieldNode(node.hyperblock, newfieldslot)
			self.translateSlotAnnotations(key, result)
			self.nodes[key] = result
		else:
			result = self.nodes[key]

		if name is not None:
			return result.name, result
		else:
			return result

	@dispatch(graph.LocalNode)
	def visitLocalNode(self, node, index, name=None):
		node = node.canonical()
		key = (node, index)		
		
		if key not in self.nodes:
			result = graph.LocalNode(node.hyperblock, node.names)
			self.translateSlotAnnotations(key, result)
			self.nodes[key] = result
		else:
			result = self.nodes[key]
				
		if name is not None:
			return name, result
		else:
			return result

	@dispatch(graph.ExistingNode)
	def visitExistingNode(self, node, index, name=None):
		node  = node.canonical()
		key   = node.name
		cache = self.dout.existing
		
		if key not in cache:
			result = graph.ExistingNode(node.name, node.ref)
			self.translateSlotAnnotations((node, index), result)
			cache[key] = result
		else:
			result = cache[key]
				
		if name is not None:
			return name, result
		else:
			return result

	@dispatch(graph.NullNode)
	def visitNullNode(self, node, index, name=None):
		if name is not None:
			return name, self.dout.null
		else:
			return self.dout.null


	@dispatch(graph.Entry)
	def processEntry(self, node):
		result = self.dout.entry
				
		for name, childnode in node.modifies.iteritems():
			for index in self.iterIndexes(childnode):
				newname, newnode = self(childnode, index, name)
				result.addEntry(newname, newnode)
		
		self.translateOpAnnotations(node, result)
		
	@dispatch(graph.Exit)
	def processExit(self, node):		
		result = graph.Exit(node.hyperblock)
		
		pred = self(node.predicate, 0)
		result.setPredicate(pred)
			
		for name, childnode in node.reads.iteritems():
			for index in self.iterIndexes(childnode):
				newname, newnode = self(childnode, index, name)
				result.addExit(newname, newnode)

		self.dout.exit = result

		self.translateOpAnnotations(node, result)


	@dispatch(graph.Split)
	def processSplit(self, node):
		# Splits will be automatically recreated.
		pass

	@dispatch(graph.Gate)
	def processGate(self, node):
		pred = self(node.predicate, 0)
		for index in self.iterIndexes(node.read):
			result = graph.Gate(node.hyperblock)

			result.setPredicate(pred)
			result.addRead(self(node.read, index))
			result.addModify(self(node.modify, index))

	@dispatch(graph.Merge)
	def processMerge(self, node):
		for index in self.iterIndexes(node.modify):
			result = graph.Merge(node.hyperblock) 
			
			for read in node.reads:
				result.addRead(self(read, index))
			
			result.addModify(self(node.modify, index))

	@dispatch(graph.GenericOp)
	def processGenericOp(self, g):
		result = graph.GenericOp(g.hyperblock, g.op)

		pred = self(g.predicate, 0)
		result.setPredicate(pred)

		trace = False

		if trace: print "!!!!", g.op

		for p in g.predicates:
			newp = self(p, 0)
			result.predicates.append(newp.addDefn(result))

		for name, node in g.localReads.iteritems():
			result.addLocalRead(name, self(node, 0))

		for node in g.localModifies:
			result.addLocalModify(None, self(node, 0))

		reads    = self.dioa.set.flatten(self.dioa.opReads[g])
		modifies = self.dioa.set.flatten(self.dioa.opModifies[g])

		if trace: 
			print "READ  ", reads
			print "MODIFY", modifies

		for name, node in g.heapReads.iteritems():
			node = node.canonical()
			for index in self.iterFieldIndexes(name):				
				if (node, index) in reads:
					newname, newnode = self(node, index, name)
					result.addRead(newname, newnode)
				else:
					if trace: print "kill read", node, index

		for name, node in g.heapPsedoReads.iteritems():
			node = node.canonical()
			modnode = g.heapModifies[name].canonical()
			for index in self.iterFieldIndexes(name):
				if (modnode, index) in modifies:
					newname, newnode = self(node, index, name)
					
					# HACK a psedo read for field on a unique, allocated object can be eliminated if it resolves to the entry.
					if newnode.isEntryNode():
						obj = node.name.object
						unique = self.dioa.isUniqueObject(obj, index)
						allocated = not self.dioa.objectIsPreexisting(obj, index)
						if unique and allocated:
							newnode = self.dout.null
					
					result.addPsedoRead(newname, newnode)
				else:
					self.connect(name, node, modnode, index)
					if trace: print "bypass", node, index

		for name, node in g.heapModifies.iteritems():
			node = node.canonical()
			for index in self.iterFieldIndexes(name):
				if (node, index) in modifies:				
					newname, newnode = self(node, index, name)
					result.addModify(newname, newnode)
				else:
					if trace: print "kill mod", node, index
					
		if trace: print

		self.translateOpAnnotations(g, result)

	def _mapFields(self, value):
		if value:
			result = frozenset([self(*field) for field in value])
		else:
			result = value
		return result

	def _mapObjects(self, value):
		if value:
			result = frozenset([self.replacementObject(*obj) for obj in value])
		else:
			result = value			
		return result

	def makeCorrelatedAnnotation(self, data):
		return annotations.CorrelatedAnnotation(self.dioa.set.flatten(data), data)

	def translateSlotAnnotations(self, slot, result):
		values = self.dioa.getValue(*slot)

		# Predicates will have binary values, so skip remapping them		
		if not slot[0].isPredicate():
			values = self.objMapper(values)
		
		values = self.makeCorrelatedAnnotation(values)
		unique = self.dioa.isUniqueSlot(*slot)
				
		annotation = annotations.DataflowSlotAnnotation(values, unique)

		result.annotation = annotation
		
	def translateOpAnnotations(self, g, result):
		reads     = self.makeCorrelatedAnnotation(self.fieldMapper(self.dioa.opReads[g]))
		modifies  = self.makeCorrelatedAnnotation(self.fieldMapper(self.dioa.opModifies[g]))
		allocates = self.makeCorrelatedAnnotation(self.objMapper(self.dioa.opAllocates[g]))
		
		mask      = self.dioa.opMask(g)
		
		annotation = annotations.DataflowOpAnnotation(reads, modifies, allocates, mask)
		
		result.annotation = annotation
	
	def translateObjectAnnotations(self, obj, result):
		preexisting = self.dioa.objectIsPreexisting(*obj)
		unique = self.dioa.isUniqueObject(*obj)
		mask = self.dioa.objectExistanceMask[obj]
		
		annotation = annotations.DataflowObjectAnnotation(preexisting, unique, mask)
		
		result.annotation = annotation
									
	def process(self):
		epn, ep = self(self.dataflow.entryPredicate, 0, '*')
		self.dout.entryPredicate = ep
		
		for op in self.order:
			self(op)
		
		# TODO Information about correlations?
			
		return self.dout

# Correlated analysis gives different versions
# of the same object an "index"
# Flattening turns indexed nodes into concrete dataflow nodes
# Flattening also ads annotations
def evaluateDataflow(compiler, dataflow, order, dioa):
	flattener = DataflowFlattener(compiler, dataflow, order, dioa)
	dataflow = flattener.process()
	dce.evaluateDataflow(dataflow)
	return dataflow
