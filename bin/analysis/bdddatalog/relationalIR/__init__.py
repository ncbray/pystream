from __future__ import absolute_import

import PADS.StrongConnectivity

from . import relationalast
from . interpreter import Interpreter
from .. datalogIR.optimizer import makePDG, makeEDG
from .. datalogIR import datalogast
from . reducerenames import reduceRenames

from util.visitor import StandardVisitor

from . printprogram import PrintProgram

import collections

specialSymbols = set(('_', '*'))

class StratificationError(Exception):
	pass

def findSCC(G):
	return [tuple(C) for C in PADS.StrongConnectivity.StronglyConnectedComponents(G)]

class HackLoop(object):
	def __init__(self, body):
		self.body = body

	def dump(self, indent=''):
		print indent+"Loop"
		indent += '|'

		for e in self.body:
			if isinstance(e, HackLoop):
				e.dump(indent)
			else:
				print indent+repr(e)

class BuildDJ(object):
	def __init__(self,G,inital):
		self.order = 0
		self.currentLevel = 0
		self.pre = {}
		self.info = {}
		self.loops = []

		self.parent = {}
		self.level  = {}

		self.partitionedLoops = collections.defaultdict(lambda: collections.defaultdict(list))
		
		dispatch = [self.backedge,self.preorder,self.postorder]
		for v,w,edgetype in PADS.DFS.search(G,inital):
			dispatch[edgetype](v,w)

		self.postprocess()
		self.mergeLoops()

	def preorder(self,parent,child):
		assert not child in self.pre
		self.pre[child] = self.order
		self.parent[child] = parent
		self.level[child] = self.currentLevel

		self.order += 1
		self.currentLevel += 1

	def postorder(self,parent,child):

		assert not child in self.info
		info = (self.pre[child], self.order)

		self.currentLevel -= 1
		self.order += 1
		
		self.info[child] = info


	def backedge(self,source,destination):
		if self.level[source] >= self.level[destination]:
			self.loops.append((source, destination))

	def postprocess(self):
		for source, destination in self.loops:			
			sinfo = self.info[source]
			dinfo = self.info[destination]
			slevel = self.level[source]
			dlevel = self.level[destination]

			d1 = sinfo[0] < dinfo[0] and sinfo[1] > dinfo[1]
			if d1: continue
			
			d2 = sinfo[0] >= dinfo[0] and sinfo[1] <= dinfo[1]
			
##			print "LOOP", d2
##			print sinfo, dinfo
##			print slevel, dlevel
##		
##			print source
##			print destination

			self.partitionedLoops[dlevel][slevel].append((source, destination, d2))

	def structure(self, e):
		if not e in self.elut:
			self.elut[e] = e
		return self.elut[e]

	def mergeLoops(self):
		self.uf = PADS.UnionFind.UnionFind()
		
		dlevels = self.partitionedLoops.keys()
		dlevels.sort(reverse=True)

		self.elut = {}

		for dlevel in dlevels:
			lloops = self.partitionedLoops[dlevel]

			slevels = lloops.keys()
			slevels.sort() # Not reversed, deal with smallest loops first.

			for slevel in slevels:
				loops = lloops[slevel]
				for source, dest, reduceable in loops:
					print source
					print dest
					print reduceable
					print

					if reduceable:
						self.collapseLoop(source, dest)

	def collapseLoop(self, source, dest):
		source = self.uf[source]
		dest = self.uf[dest]

		current = source
		body = [source]

		while current != dest:
			current = self.uf[self.parent[current]]
			body.append(current)


		body.reverse()

		# Collapse the loop
		self.uf.union(*body)
		self.parent[self.uf[dest]] = self.parent[dest]

		body = [self.structure(e) for e in body]

		if len(body) == 1 and isinstance(body[0], HackLoop):
			return

##			print "Loop"
##			for b in body:
##				print b
##			print

		l = HackLoop(body)
		l.dump()
		self.elut[self.uf[dest]] = l

def havlakFindLoops(partition):
	reads, writes = makeEDG(partition)


	#scc = findSCC(reads)

	entry = set()
	for e in partition:
		if not reads[e]:
			print "Entry E", e
			entry.add(e)

	writes[None] = tuple(entry)
	dj = BuildDJ(writes, None)


def findOrderedSCC(partition, indent=''):
	return havlakFindLoops(partition)
	
	if len(partition) == 0:
		return []
	
	reads, writes = makeEDG(partition)

	scc = findSCC(reads)


##	entry = set()
##	for e in partition:
##		if not reads[e]:
##			#print "Entry E", e
##			entry.add(e)


	# Get rid of the individual "input" strata.		
##	old = scc
##	scc = filter(lambda g: not entry.issuperset(g), scc)
##	assert len(scc) < len(old)
##	entry = tuple(entry)
##	scc.append(entry)


	strataReads, strataWrites, strataLoops = getStrataDep(scc, reads, writes)


	#assert len(strataReads) == len(scc), (len(strataReads), len(scc))

	#order = reversePostorder(strataWrites, entry)

	entry = set()
	for sg in scc:
		w = strataReads[sg]
		if not w:
			entry.add(sg)

	strataWrites[None] = tuple(entry)
	order = reversePostorder(strataWrites, None)

	#assert len(order) == len(scc), (len(order), len(scc))

	#print "ORDERED"
	for sg in order:
		if sg == None: continue
		
		assert isinstance(sg, (list, tuple, set)), type(sg)
		if not strataLoops[sg]:
			for e in sg:
				print indent, e
		else:
			#print "LOOP"
			print indent+'|', sg[0]
			findOrderedSCC(sg[1:], indent+'|')
	
	return order


def findLoops(ast):
	return
##	findOrderedSCC(ast.expressions)
##	return
	
	reads, writes = makeEDG(ast.expressions)

	scc = findSCC(reads)
	for sg in scc:
		findSubloops(reads, sg)

def findSubloops(g, sg, indent=''):
	newg = {}
	inputs = set()

	# Arbitrarily choose the head.
	head = sg[0]

	for e in sg:
		newg[e] = set()
		for dep in g[e]:
			if dep in sg and not dep==head:
				newg[e].add(dep)
			else:
				inputs.add(e)

	scc = findSCC(newg)

	dep = {}

##	order = reversePostorder(scc, inputs)
	
	for ssg in scc:
		if len(ssg) > 1:
			findSubloops(g, ssg, indent+'\t')
		else:
			for e in ssg:
				print e
				print
	print

def getStrataDep(scc, reads, writes):
	relToStrata = strataMap(scc)
	
	strataReads = collections.defaultdict(set)
	strataWrites = collections.defaultdict(set)
	strataLoops = collections.defaultdict(lambda: False)

	for g in scc:
		for relation in g:
			for read in reads[relation]:
				strataRead = relToStrata[read]
				if strataRead != g:
					strataReads[g].add(strataRead)

			for write in writes[relation]:
				strataWrite = relToStrata[write]
				if strataWrite != g:
					strataWrites[g].add(strataWrite)
				else:
					strataLoops[g] = True

	return strataReads, strataWrites, strataLoops

def strataMap(scc):
	relToStrata = {}
	for g in scc:
		for relation in g:
			relToStrata[relation] = g
	return relToStrata

def stratify(ast):
	findLoops(ast)
	
	reads, writes = makePDG(ast)

	inputs = set()
	for r in ast.relations:
		if r.io == 'input':
			assert not writes[r]
			inputs.add(r)
	
	scc = findSCC(reads)

	# Get rid of the individual "input" strata.
	scc = filter(lambda g: not inputs.issuperset(g), scc)

	inputs = tuple(inputs)
	scc.append(inputs)


	# Check for stratification.
	relToStrata = strataMap(scc)
	for e in ast.expressions:
		inv = e.inversions()
		strata = relToStrata[e.target.relation]

		# Does the expression invert a relation from the same strata as its target?
		common = inv.intersection(strata)

		if common:
			raise StratificationError, "%s cannot be stratified due to inversion of %s" % (str(e), str(tuple(common)))

	strataReads, strataWrites, strataLoops = getStrataDep(scc, reads, writes)

	order = reversePostorder(strataReads, inputs)
	return order

def reversePostorder(g, inital):
	order = list(PADS.DFS.postorder(g, inital))
	order.reverse()
	return order

def temp(ast):
	strata = makeStrata(ast)



def processStrata(builder, ast, strata):
	strata = set(strata)
	
	expr = collections.defaultdict(list)

	for r in strata:
		builder.addRelation(r)

	for e in ast.expressions:
		if e.target.relation in strata:
			expr[e.target.relation].append(e)
	

	# Classify the rules in each strata
	# initalize: only depends on previous strata, no iteration needed.
	# iterate: depends on current strata
	# closure: subgoals depend on target, should iterate until convergence.
	# Identifying closures is a hack, we should really be identifying
	# arbitrary loops.
	
	initalize = []
	iterate = []
	closure = set()
	reorder = set()


	def classify(e):
		isIter = False
		isClosure = False
		externalCount = 0
		for term in e.terms:
			relations = set()
			term.relations(relations)

			for relation in relations:
				if relation in strata:
					isIter = True
				else:
					externalCount += 1
				
				if relation == e.target.relation:
					isClosure = True
		if isIter:
			if isClosure:
				closure.add(e)
			iterate.append(e)
		else:
			initalize.append(e)

		if externalCount > 1:
			reorder.add(e)

	for r in strata:
		for e in expr[r]:
			classify(e)

	# Prioritize smaller cycles?
	# Prioritize smaller rules?

	# TODO better ordering of expressions.
	block = relationalast.InstructionBlock()
	
	for e in initalize:
		ex = process(builder, e)
		block.addInstruction(ex)


	if iterate:
		innerblock = relationalast.InstructionBlock()
		for e in iterate:
			ex = process(builder, e)

			if e in closure:
				b = relationalast.InstructionBlock()
				b.addInstruction(ex)
				b = relationalast.Loop(b)
			else:
				b = ex
			innerblock.addInstruction(b)
		iterate = relationalast.Loop(innerblock)
		block.addInstruction(iterate)
	
	strata = relationalast.Loop(block)

	return strata

# Assuming the terms are joined in order, find the variables that can be abstracted at each step.
def makeLiveList(finalLive, terms):
	live = []
	currentLive = finalLive-specialSymbols

	for term in reversed(terms):
		live.append(currentLive)
		args = term.symbols()-specialSymbols
		a = args-currentLive
		currentLive = currentLive.union(a)

	live.reverse()

	return live

class BddInfo(object):
	def __init__(self, names, symbols, temporary):
		assert isinstance(names, dict)
		assert isinstance(symbols, dict)
		assert isinstance(temporary, str)

		assert len(names) >= len(symbols)
		for name, s in names.iteritems():
			assert s in specialSymbols or s in symbols, s

		for s, name in symbols.iteritems():
			assert isinstance(s, str), s
			assert name in names, sname

		self.names 	= names 	# name -> symbol
		self.symbols 	= symbols 	# symbol -> name
		self.temporary 	= temporary

	def isDegenerate(self):
		# Do multiple names map to the same symbol?
		s = set()
		for name, symbol in self.names.iteritems():
			if not symbol in specialSymbols:
				if symbol in s:
					return True
				s.add(symbol)
		return False

	def eliminateDegenerate(self, builder):
		if self.isDegenerate():
			# Rename so only one name maps to a given symbol.
			symbols = {}
			names 	= {}
			rn 	= {}

			for name, symbol in self.names.iteritems():
				if symbol in specialSymbols:
					newName = builder.newRename(name)
				else:
					if not symbol in symbols:
						symbols[symbol] = builder.newRename(name)
					newName = symbols[symbol]

				rn[name] = newName
				names[newName] = symbol

			temp = builder.emitRename(self.temporary, rn)

			# Make sure the names are different
			builder.namesMustBeDifferent(names.keys())

			info = BddInfo(names, symbols, temp)

			return info
		else:
			return self

	def eliminateDead(self, liveSymbols, builder):
		# Find unneeded variables.
		abstractNames = set()
		
		for name, symbol in self.names.iteritems():
			if not symbol in liveSymbols:
				abstractNames.add(name)

		return self.project(abstractNames, builder)

	def project(self, abstractNames, builder):
		# Eliminate unneeded variables.
		if abstractNames:
			names = {}
			for name, symbol in self.names.iteritems():
				if not name in abstractNames:
					names[name] = symbol

			symbols = {}
			for symbol, name in self.symbols.iteritems():
				if not name in abstractNames:
					symbols[symbol] = name
			
			temp = builder.emitProject(self.temporary, abstractNames)
			return BddInfo(names, symbols, temp)
		else:
			return self

	def invert(self, builder):
		temp = builder.emitInvert(self.temporary)
		return BddInfo(self.names, self.symbols, temp)


	def eliminateAny(self, builder):
		abstractNames = set()
		for name, symbol in self.names.iteritems():
			if symbol == '_':
				abstractNames.add(name)
		return self.project(abstractNames, builder)

	def join(self, other, builder):
		names = {}
		symbols = {}
		arn = calcRename(self, names, symbols, builder)
		brn = calcRename(other, names, symbols, builder)

		assert len(names) <= len(self.names)+len(other.names)

		# Make sure the names are different
		builder.namesMustBeDifferent(names.keys())

		# Rename and join the inputs
		tempA = builder.emitRename(self.temporary, arn)
		tempB = builder.emitRename(other.temporary, brn)
		temp  = builder.emitJoin(tempA, tempB)

		return BddInfo(names, symbols, temp)

def calcRename(info, names, symbols, builder):
	rename = {}
	
	for name, symbol in info.names.iteritems():
		if symbol in specialSymbols:
			newName = builder.newRename(name)
			names[newName] = symbol
		else:
			if not symbol in symbols:
				symbols[symbol] = builder.newRename(name)

			newName = symbols[symbol]
			names[newName] = symbol

		assert not name in rename
		rename[name] = newName

	return rename

def buildTermLUT(args, currentNames, names, symbols):
	for symbol, name in zip(args, currentNames):
		if isinstance(symbol, (list, tuple)):
			buildTermLUT(symbol, name, names, symbols)
		else:
			names[name] = symbol	
			symbols[symbol] = name
	

def loadConditioned(term, builder):
	termNames, temp = builder.cachedLoad(term.relation)

	names 	= {}
	symbols = {}


	buildTermLUT(term.args(), termNames, names, symbols)

	info = BddInfo(names, symbols, temp)
	info = info.eliminateAny(builder)
	info = info.eliminateDegenerate(builder)

	return info

def getTerm(term, builder):
	if isinstance(term, datalogast.Invert):
		info = loadConditioned(term.term, builder)
		return info.invert(builder)
	else:
		return loadConditioned(term, builder)

def joinTerms(builder, finalLive, terms):
	liveList = makeLiveList(finalLive, terms)

	info = None
	
	for term, liveSymbols in zip(terms, liveList):
		if info == None:
			info = getTerm(term, builder)
		else:
			newInfo = getTerm(term, builder)
			info = info.join(newInfo, builder)
			
		info = info.eliminateDead(liveSymbols, builder)

		assert not '_' in info.symbols, e
		assert not '*' in info.symbols, e

	return info

def process(builder, e):
	builder.beginExpression()

	target = e.target
	terms = e.terms
	targetSymbols = target.symbols()-specialSymbols

	info = joinTerms(builder, targetSymbols, terms)

	# Union with target.
	assert len(info.symbols) == len(targetSymbols), (e,  target, info.symbols)

	targetNames, original = builder.cachedLoad(target.relation)



	names = {}
	symbols = {}
	buildTermLUT(target.args(), targetNames, names, symbols)


	arn = {}
	for arg, name in symbols.iteritems():
		if not arg in specialSymbols:
			assert arg in info.symbols
			arn[info.symbols[arg]] = name

	update = builder.emitRename(info.temporary, arn)

	currentTemp = builder.emitUnion(original, update)
	builder.emitStore(currentTemp, target.relation.name)

	# Build the expression.
	ex = builder.currentBlock

	rmod, rread = e.dependancies()

	read = set([relation.name for relation in rread])
	modify = set([rmod.name])

	builder.endExpression()

	return relationalast.Expression(ex, read, modify, e)

def flatten(names):
	outp = []
	for n in names:
		if isinstance(n, (list, tuple)):
			outp.extend(flatten(n))
		else:
			assert isinstance(n, int)
			outp.append(n)
	return tuple(outp)

class RelationalProgramBuilder(object):
	def __init__(self):
		self.currentName = 0
		self.currentTemp = 0

		self.nameDomains = {}
		self.relationNames = {}

		self.nameGroups = []
		self.renames = []

		self.expressions = []

		self.currentBlock = None

		self.loadCache = {}

	def cachedLoad(self, relation):
		name = relation.name
		if not name in self.loadCache:
			termNames = self.relationNames[relation]
			temp = self.emitLoad(name)
			self.loadCache[name] = (termNames, temp)
		return self.loadCache[name]

	def newTemp(self):
		temp = self.currentTemp
		self.currentTemp += 1
		return 't' + str(temp)

	def newRename(self, name):
		if isinstance(name, int):
			assert name in self.nameDomains, name
			return self.newName(self.nameDomains[name])
		else:
			return tuple([self.newRename(n) for n in name])

	def newName(self, domain):
		assert isinstance(domain, datalogast.Domain), domain
		temp = self.currentName
		self.currentName += 1
		self.nameDomains[temp] = domain
		return temp

	def newNamesFromFields(self, fields):
		names = []
		for n, d in fields:
			if isinstance(d, datalogast.Structure):
				names.append(self.newNamesFromFields(d.fields))
			else:
				names.append(self.newName(d))
		return tuple(names)

	def addRelation(self, r):
		names = self.newNamesFromFields(r.fields)
		#print r.name, names
		self.relationNames[r] = names
		self.namesMustBeDifferent(names)

	def namesMustBeDifferent(self, names):
		names = flatten(names)
		#print "DIFFERENT", names
		self.nameGroups.append(names)

	def beginExpression(self):
		self.loadCache = {}
		
		b = relationalast.InstructionBlock()
		self.expressions.append(b)
		self.currentBlock = b

	def endExpression(self):
		self.currentBlock = None

	def __emit(self, cls, *args):
		t = self.newTemp()
		op = cls(t, *args)
		self.currentBlock.addInstruction(op)
		return t

	def emitLoad(self, name):
		return self.__emit(relationalast.Load, name)

	def flattenRename(self, k, v, rn):
		if isinstance(k, int):
			assert isinstance(v, int)
			assert not k in rn
			rn[k] = v
		else:
			assert len(k) == len(v)
			for ki, vi in zip(k, v):
				self.flattenRename(ki, vi, rn)

	def emitRename(self, source, rn):
		assert isinstance(rn, dict)
		newRN = {}
		for k, v in rn.iteritems():
			self.flattenRename(k, v, newRN)

		self.renames.append(newRN)
		return self.__emit(relationalast.Rename, source, newRN)

	def emitJoin(self, a, b):
		return self.__emit(relationalast.Join, a, b)

	def emitProject(self, source, fields):
		fields = flatten(fields)
		return self.__emit(relationalast.Project, source, fields)

	def emitUnion(self, a, b):
		return self.__emit(relationalast.Union, a, b)

	def emitInvert(self, a):
		return self.__emit(relationalast.Invert, a)		
	
	def emitStore(self, target, name):	
		op = relationalast.Store(target, name)
		self.currentBlock.addInstruction(op)






def coalesce(prgm):
	duf = DefUseFinder()
	duf.walk(prgm)
	kill, replace = coalesceKillReplace(duf.defs, duf.uses)
	return KillReplaceRewrite(kill, replace).walk(prgm)

			
def coalesceKillReplace(defs, uses):
	kill = set()
	replace = {}

	for var in defs.keys():
		if var in defs:
			op = defs[var]
			if isinstance(op, relationalast.Project):
				parent = defs[op.source]

				# Coalesce Joins and Projects into RelProds
				if isinstance(parent, relationalast.Join) and len(uses[parent.target]) == 1:
					newOp = relationalast.RelProd(op.target, parent.left, parent.right, op.fields)

					defs[var] = newOp

					uses[parent.left].remove(parent)
					uses[parent.right].remove(parent)
					
					uses[parent.left].append(newOp)
					uses[parent.right].append(newOp)

					replace[parent] = newOp
					kill.add(op)
				
			# Kill dead expressions
			if not var in uses:
				kill.add(defs[var])
				del defs[var]

	return kill, replace

class DefUseFinder(StandardVisitor):
	def __init__(self):
		self.defs = {}
		self.uses = {}

	def addDef(self, target, op):
		assert not target in self.defs
		self.defs[target] = op
		self.uses[target] = []

	def addUse(self, target, op):
		self.uses[target].append(op)

	def visitLoad(self, node):		
		self.addDef(node.target, node)

	def visitStore(self, node):		
		self.addUse(node.target, node)

	def visitRename(self, node):		
		self.addDef(node.target, node)
		self.addUse(node.source, node)

	def visitProject(self, node):		
		self.addDef(node.target, node)
		self.addUse(node.source, node)

	def visitInvert(self, node):		
		self.addDef(node.target, node)
		self.addUse(node.expr, node)

	def visitUnion(self, node):		
		self.addDef(node.target, node)
		self.addUse(node.left, node)
		self.addUse(node.right, node)

	def visitJoin(self, node):
		self.addDef(node.target, node)
		self.addUse(node.left, node)
		self.addUse(node.right, node)

	def visitInstructionBlock(self, node):
		for op in node.instructions:
			self.visit(op)

	def visitLoop(self, node):
		self.visit(node.block)

	def visitExpression(self, node):
		self.visit(node.block)

	def visitProgram(self, node):
		self.visit(node.body)


class KillReplaceRewrite(StandardVisitor):
	def __init__(self, kill, replace):
		self.kill = kill
		self.replace = {}

		# A bit of a hack?
		for k, v in replace.iteritems():
			while v in replace:
				v = replace[v]
			self.replace[k] = v

	def visitLoad(self, node):		
		return self.replace.get(node, node)

	def visitStore(self, node):		
		return self.replace.get(node, node)

	def visitRename(self, node):		
		return self.replace.get(node, node)

	def visitProject(self, node):		
		return self.replace.get(node, node)

	def visitInvert(self, node):		
		return self.replace.get(node, node)

	def visitUnion(self, node):		
		return self.replace.get(node, node)

	def visitJoin(self, node):
		return self.replace.get(node, node)

	def visitInstructionBlock(self, node):
		rewriten = node.__class__()
		
		for op in node.instructions:
			if not op in self.kill:
				op = self.visit(op)

				# Doesn't work quite right if intermediate results should have been killed.
				if not op in self.kill:
					rewriten.addInstruction(op)
		return rewriten

	def visitLoop(self, node):
		return node.__class__(self.visit(node.block))

	def visitExpression(self, node):
		n = node.__class__(self.visit(node.block), node.read, node.modify, node.datalog)
		return n

	def visitProgram(self, node):
		return node.__class__(node.domains, node.structures, node.relations, node.nameDomains, node.relationNames, self.visit(node.body))







# Lower datalog into the relational IR
def relationalFromDatalog(ast):
	stratas = stratify(ast)

	builder = RelationalProgramBuilder()

	b = relationalast.InstructionBlock()
	for strata in stratas:
		s = processStrata(builder, ast, strata)
		b.addInstruction(s)
	body = relationalast.Loop(b)

	prgm = relationalast.Program(ast.domains, ast.structures, ast.relations, builder.nameDomains, builder.relationNames, body)
	
	prgm = coalesce(prgm)
	prgm = reduceRenames(prgm, builder.currentName)
	
	#PrintProgram().walk(prgm, '')
	return prgm


def interpreterFromRelational(prgm, domainBindings):
	return Interpreter(prgm, domainBindings)
