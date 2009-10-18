from analysis.dataflowIR import graph

from analysis.dataflowIR.traverse import dfs

def findLoadSrc(g):
	for node in g.heapReads.itervalues():
		defn = node.canonical().defn
		return defn

def attemptTransform(g):
	# Is the load unused or invalid?
	if len(g.localModifies) != 1:
		return False
	
	defn = findLoadSrc(g)

	if isinstance(defn, graph.GenericOp) and defn.isStore():
		if not g.canonicalpredicate is defn.canonicalpredicate:
			return False
		
		# Make sure the load / store parameters are identical
		# expr
		if not g.localReads[g.op.expr].canonical() == defn.localReads[defn.op.expr].canonical(): 
			return False

		# field type
		if not g.op.fieldtype == defn.op.fieldtype:
			return False

		# field name
		if not g.localReads[g.op.name].canonical() == defn.localReads[defn.op.name].canonical(): 
			return False

		# Make sure the heap read / modify is identical
		
		reads = frozenset([node.canonical() for node in g.heapReads.itervalues()])
		modifies = frozenset([node.canonical() for node in defn.heapModifies.itervalues()])

		if reads != modifies:
			return False
		
		# It's sound to bypass the load.
		src = defn.localReads[defn.op.value]
		dst = g.localModifies[0]
				
		dst.canonical().redirect(src)
		g.localModifies = []

		return True

	return False

def evaluateDataflow(dataflow):
	loads = set()
	
	def collect(node):
		if isinstance(node, graph.GenericOp) and node.isLoad():
			loads.add(node)
	
	dfs(dataflow, collect)
	
	print "LOADS", len(loads)
	
	eliminated = 0
	
	# HACK keep evaluating each load until no further transforms are possible.
	changed = True
	while changed:
		changed = False
		for load in loads:
			if attemptTransform(load):
				eliminated += 1
				changed = True 
	
	print "ELIMINATED", eliminated