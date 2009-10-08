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
			xtype = obj.xtype
			indexedType = self.compiler.storeGraph.canonical.indexedType(xtype)
			replacement = self.compiler.storeGraph.regionHint.object(indexedType)
			self.objects[key] = replacement
		else:
			replacement = self.objects[key]
		return replacement

	def replacementField(self, name, index):
		key = (name, index)
		if key not in self.fields:
			newobj = self.replacementObject(name.object, index)
			newfield = newobj.field(name.slotName, self.compiler.storeGraph.regionHint)
			self.fields[key] = newfield
		else:
			newfield = self.fields[key]
		return newfield

	@dispatch(graph.Entry)
	def processEntry(self, node):
		for name, child in node.modifies.iteritems():
				count = self.dioa.numValues(child)

				if count > 1:				
					print name
					print child
					print count
				
					for i in range(count):
						newfield = self.replacementField(name, i)
						print newfield
						
					print			

	@dispatch(graph.Exit)
	def processExit(self, node):
		pass

	@dispatch(graph.Split)
	def processSplit(self, node):
		pass

	@dispatch(graph.Gate)
	def processGate(self, node):
		pass

	@dispatch(graph.Merge)
	def processMerge(self, node):
		pass

	@dispatch(graph.GenericOp)
	def processGenericOp(self, node):
		pass

	def process(self):
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
