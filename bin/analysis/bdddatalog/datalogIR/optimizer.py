from __future__ import absolute_import

import PADS.DFS

from . import datalogast

import collections

def makePDG(ast):
	reads = {}
	writes = {}
	
	for t in ast.relations:
		reads[t] = set()
		writes[t] = set()

	for e in ast.expressions:
		write, read = e.dependancies()

		writes[write].update(read)
		for r in read:
			reads[r].add(write)

	return reads, writes

# Predicate -> expression
def makePEDG(ast):
	reads  = {}
	writes = {}

	for r in ast.relations:
		reads[r] = []
		writes[r] = []

	for e in ast.expressions:
		write, read = e.dependancies()
		writes[write].append(e)

		for r in read:
			reads[r].append(e)

	return reads, writes

def getExprDependancies(expressions):
	reads = collections.defaultdict(set)
	writes = collections.defaultdict(set)

	for e in expressions:
		write, read = e.dependancies()

		writes[write].add(e)
		
		for r in read:
			reads[r].add(e)
	return reads, writes

def norm(a, b):
	res = collections.defaultdict(set)

	for relation, exprs in a.iteritems():
		for expr in exprs:
			res[expr].update(b[relation])
	return res

# The expression dependance graph.
def makeEDG(expressions):
	assert isinstance(expressions, (list, tuple))
	
	reads, writes = getExprDependancies(expressions)
	er = norm(reads, writes)
	ew = norm(writes, reads)	
	return er, ew




def findReachable(outputs, writes):
	writes[None] = outputs
	s = set(PADS.DFS.postorder(writes, None))
	s.remove(None)
	return s

def removeUnused(ast):
	changed = False
	reads, writes = makePDG(ast)
	outputs = filter(lambda r: r.io == 'output', ast.relations)
	live = findReachable(outputs, writes)

	# HACK prevent inputs from being removed.
	inputs = filter(lambda r: r.io == 'input', ast.relations)
	live.update(inputs)
	
	#live.update(outputs) # Importaint, outputs may not be reachable from self?

	if len(live) != len(ast.relations):
		#dead = set(ast.relations) - live
		# TODO warn of dead relations.

		# Remove dead relations.
		ast.relations = filter(lambda r: r in live, ast.relations)

		# Remove expressions that write to dead relations.
		ast.expressions = filter(lambda e: e.target.relation in live, ast.expressions)

		changed = True

	return ast, changed

def removeUndefined(ast):
	changed = False
	# Find relations that are never defined.
	reads, writes = makePDG(ast)
	inputs = filter(lambda r: r.io == 'input', ast.relations)
	live = findReachable(inputs, reads)

	assert live, ("Everything is dead?", inputs)

	if len(live) != len(ast.relations):
		undefined = set(ast.relations)-live
		print "WARNING: undefined relations are used -", undefined
		assert False, "Program uses undefined relations: %s.  Aborting." % str(undefined)

		#changed = True

	return ast, changed

def removeUnusedDomains(ast):
	changed = False
	# Find unused domains.
	livedomains = set()
	for r in ast.relations:
		for name, domain in r.fields:
			livedomains.add(domain)

	# Remove unused domains.
	if len(livedomains) != len(ast.domains):
		ast.domains = filter(lambda d: d in livedomains, ast.domains)	
		changed = True

	return ast, changed

def removeTemporaries(ast):
	#return ast, False # HACK disabled
	
	changed = False

	reads, writes = makePEDG(ast)

	temporary = filter(lambda r: r.io == 'internal' and len(reads[r]) == 1 and len(writes[r]) ==1, ast.relations)

	# TODO make sure a temporary is only -used- once within a rule.
	
	for relation in temporary:
		assert len(reads[relation]) == 1
		assert len(writes[relation]) == 1

		tempE = writes[relation][0]
		useE = reads[relation][0]

		# HACK doesn't detect hierachial collapsed symbols.
		assert len(tempE.target.args()) == len(set(tempE.target.args())), "Can't deal with a collapsing target, yet: %s" % str(tempE)

		uses = filter(lambda t: t.relation == relation, useE.terms)
		assert len(uses) == 1
		use = uses[0]
		index = useE.terms.index(use)

		oldSymbols = tempE.symbols()
		newSymbols = useE.symbols()

		# Directly map the symbols from the target.
		lut = {}
		for oldS, newS in zip(tempE.target.args(), use.args()):
			lut[oldS] = newS

		# Find unique names for the internal signals.
		for oldS in oldSymbols:
			if not oldS in lut:
				newS  = oldS
				if newS != '_' and newS != '*':
					while newS in newSymbols:
						newS = '_'+newS
				lut[oldS] = newS

		transE = tempE.translate(lut)

		newTerms = useE.terms[:index]
		newTerms.extend(transE.terms)
		newTerms.extend(useE.terms[index+1:])

		newE = datalogast.Expression(useE.target, newTerms)

		# Replace the expressions with the merged version
		ast.expressions.remove(tempE)
		ast.expressions.remove(useE)
		ast.expressions.append(newE)

		changed = True
	
	return ast, changed

def simplifyAST(ast):
	assert ast.expressions, "NULL Program."
	
	changed = True
	while changed:
		changed = False
		ast, c0 = removeUnused(ast)
		ast, c1 = removeUndefined(ast)
		ast, c2 = removeTemporaries(ast)
		changed = c1 or c2 # No point in iterating if only c0 changes


	ast, c3 = removeUnusedDomains(ast)
	ast.regenerateSymbolTable()
	
	return ast
