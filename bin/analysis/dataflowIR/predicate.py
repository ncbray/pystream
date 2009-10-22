from util.typedispatch import *

from analysis.dataflowIR import graph

from .traverse import dfs
from util.graphalgorithim.dominator import dominatorTree

class PredicateGraph(object):
	def __init__(self):
		self.entry = None
		self.exit  = None
		self.forward = {}
		self.reverse = {}
		self.tree  = None
		self.idom  = None
	
	def _declare(self, pred):
		if pred not in self.forward:
			self.forward[pred] = []	
			self.reverse[pred] = []	
	
	def depends(self, src, dst):
		src = src.canonical()
		dst = dst.canonical()
		
		assert src.isPredicate(), src
		assert dst.isPredicate(), dst
		
		self._declare(src)
		self._declare(dst)
		
		self.forward[src].append(dst)
		self.reverse[dst].append(src)
	
	def finalize(self):
		# For simple graphs, there may be no dependencies,
		# so make sure the entry is declared
		self._declare(self.entry)
		
		# Generate predicate domination information
		self.tree, self.idom = dominatorTree(self.forward, self.entry)
	
	def dominates(self, src, dst):
		src = src.canonical()
		dst = dst.canonical()

		if src is dst:
			return True
		
		if dst in self.idom:
			return self.dominates(src, self.idom[dst])
		
		return False
	
class PredicateGraphBuilder(TypeDispatcher):
	def __init__(self):
		TypeDispatcher.__init__(self)
		self.pg = PredicateGraph()
	
	@dispatch(graph.Entry, graph.Split, graph.Gate,
			graph.FieldNode, graph.LocalNode,
			graph.NullNode, graph.ExistingNode,
			graph.PredicateNode)
	def visitJunk(self, node):
		pass # Does not generate new predicates

	@dispatch(graph.Exit)
	def visitExit(self, node):
		self.pg.exit = node.canonicalpredicate

	@dispatch(graph.GenericOp)
	def visitGenericOp(self, node):
		# Generic ops may generate new predicates
		for child in node.predicates:
			self.pg.depends(node.predicate, child)

	@dispatch(graph.Merge)
	def visitMerge(self, node):
		if node.isPredicateOp():
			# Merges may generate new predicates
			dst = node.modify
			for prev in node.reads:
				assert isinstance(prev.defn, graph.Gate), prev.defn
				src = prev.defn.read
				self.pg.depends(src, dst)
	
	def process(self, dataflow):
		self.pg.entry = dataflow.entryPredicate.canonical()
		dfs(dataflow, self)
		self.pg.finalize()
		return self.pg

def buildPredicateGraph(dataflow):
	pgb = PredicateGraphBuilder()
	return pgb.process(dataflow)
