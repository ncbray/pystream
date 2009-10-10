from util.typedispatch import *
from language.python import ast
from analysis.dataflowIR import graph

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

	def replacementObject(self, obj, index):
		key = (obj, index)
		if key not in self.objects:
			if self.dioa.getCount(obj) > 1:
				xtype = obj.xtype
				indexedType = self.compiler.storeGraph.canonical.indexedType(xtype)
				replacement = self.compiler.storeGraph.regionHint.object(indexedType)
			else:
				replacement = obj # HACK
				
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
			pred = self(node.canonicalpredicate, 0)
			
			print "SOURCE", node.source
			
			result = graph.PredicateNode(node.hyperblock, pred, None, node.name)
			self.nodes[key] = result
			
			
			print node
			print result
			print
			
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
			pred = self(node.canonicalpredicate, 0)
			result = graph.FieldNode(node.hyperblock, pred, newfieldslot)
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
			pred = self(node.canonicalpredicate, 0)
			result = graph.LocalNode(node.hyperblock, pred, node.names)
			self.nodes[key] = result
		else:
			result = self.nodes[key]
				
		if name is not None:
			return name, result
		else:
			return result

	@dispatch(graph.ExistingNode)
	def visitExistingNode(self, node, index, name=None):
		node = node.canonical()
		key = (node, index)		
		
		if key not in self.nodes:
			result = graph.ExistingNode(node.name, node.ref)
			self.nodes[key] = result
		else:
			result = self.nodes[key]
				
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
				
	@dispatch(graph.Exit)
	def processExit(self, node):
		pred = self(node.canonicalpredicate, 0)
		
		result = graph.Exit(node.hyperblock, pred)
		result.setPredicate(pred)
			
		for name, childnode in node.reads.iteritems():
			for index in self.iterIndexes(childnode):
				newname, newnode = self(childnode, index, name)
				result.addExit(newname, newnode)

		self.dout.exit = result

	@dispatch(graph.Split)
	def processSplit(self, node):
		# Splits will be automatically recreated.
		pass

	@dispatch(graph.Gate)
	def processGate(self, node):
		pred = self(node.canonicalpredicate, 0)
		for index in self.iterIndexes(node.read):
			result = graph.Gate(node.hyperblock, pred)

			result.setPredicate(pred)

			read = self(node.read, index)
			result.addRead(read)


			modify = self(node.modify, index)
			result.addModify(modify)
						
			print index
			print node
			print result
			print

	@dispatch(graph.Merge)
	def processMerge(self, node):
		for index in self.iterIndexes(node.modify):
			result = graph.Merge(node.hyperblock) 
			
			for read in node.reads:
				read = self(read, index)
				result.addRead(read)
			
			modify = self(node.modify, index)
			result.addModify(modify)
			
			print index
			print node
			print result
			print

	@dispatch(graph.GenericOp)
	def processGenericOp(self, g):
		pred = self(g.canonicalpredicate, 0)
		result = graph.GenericOp(g.hyperblock, pred, g.op)

		result.setPredicate(pred)

		trace = True

		if trace: print "!!!!", g.op

		for p in g.predicates:
			result.predicates.append(self(p, 0).addDefn(result))

		for name, node in g.localReads.iteritems():
			result.addLocalRead(name, self(node, 0))

		for node in g.localModifies:
			result.addLocalModify(None, self(node, 0))

		reads    = self.dioa.set.flatten(self.dioa.opReads[g])
		modifies = self.dioa.set.flatten(self.dioa.opModifies[g])

		print "READ  ", reads
		print "MODIFY", modifies

		for name, node in g.heapReads.iteritems():
			node = node.canonical()
			for index in self.iterIndexes(node):
				if (node, index) in reads:
				
					newname, newnode = self(node, index, name)
					
					result.addRead(newname, newnode)
				else:
					print "kill read", node, index

		for name, node in g.heapPsedoReads.iteritems():
			node = node.canonical()
			modnode = g.heapModifies[name].canonical()
			for index in self.iterIndexes(node):
				if (modnode, index) in modifies:
					newname, newnode = self(node, index, name)
					
					result.addPsedoRead(newname, newnode)
				else:
					self.connect(name, node, modnode, index)
					# TODO byass
					print "bypass", node, index

		for name, node in g.heapModifies.iteritems():
			node = node.canonical()
			for index in self.iterIndexes(node):
				if (node, index) in modifies:				
					newname, newnode = self(node, index, name)
					
					result.addModify(newname, newnode)
				else:
					print "kill mod", node, index


		if trace: print

	def process(self):
		epn, ep = self(self.dataflow.entryPredicate, 0, '*')
		self.dout.entryPredicate = ep
		
		# HACK, entryPredicate automatically added... remove it.
		self.dout.entry.modifies = {}

		
		# TODO existing
		# TODO null
		
		for op in self.order:
			self(op)
			
		return self.dout

# Correlated analysis gives different versions
# of the same object an "index"
# Flattening turns indexed nodes into concrete dataflow nodes
# Flattening also ads annotations
def evaluateDataflow(compiler, dataflow, order, dioa):
	flattener = DataflowFlattener(compiler, dataflow, order, dioa)
	return flattener.process()
