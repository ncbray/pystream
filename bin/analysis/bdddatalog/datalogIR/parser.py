from __future__ import absolute_import

import copy

from . import datalogast

def getValue(arg):
	if isinstance(arg, SymbolProxy):
		return arg.name
	else:
		return arg

class SymbolProxy(object):
	def __init__(self, name, callback):
		self.name = name
		self.callback = callback
 
	def __call__(self, *args, **kargs):
		return self.callback('call', self.name, *args, **kargs)

	def __repr__(self):
		return self.name

	def __eq__(self, other):
		assert isinstance(other, SymbolProxy), other
		return self.callback('==', self.name, other.name)

class TermWrapper(object):
	def __init__(self, terms, callback):
		self.terms = terms
		self.callback = callback
		
		# For building the AST
	def __and__(self, other):
		assert isinstance(other, TermWrapper), (self, other)
		m = TermWrapper(self.terms+other.terms, self.callback)
		return m

	def __le__(self, other):
		assert isinstance(other, TermWrapper)
		assert len(self.terms) == 1
		e = datalogast.Expression(self.terms[0], other.terms)
		self.callback(e)
		return e

	def __invert__(self):
		assert len(self.terms) == 1 # TODO multiple inversion?
		terms = [datalogast.Invert(self.terms[0])]
		return TermWrapper(terms, self.callback)

def symbolEval(f, callback):
	symbols = {}
	# Define symbols.
	for name in f.func_code.co_names:
		if not name in symbols:
			symbols[name] = SymbolProxy(name, callback)

	eval(f.func_code, symbols)

	return symbols

def compileDomains(d, p):
	domains = []

	def domainCallback(mode, name):
		assert mode == 'call', mode
				
		d = datalogast.Domain(name)
		p.addDomain(d)

	symbolEval(d, domainCallback)



def translateSymbolicFields(p, fields):
	outfields = []
	for fname, fdomain in fields:
		if not fdomain.name in p.symbols:
			raise datalogast.UnknownDomainError, fdomain.name
		d = p.symbols[fdomain.name]
		outfields.append((fname, d))
	return outfields

def compileStructures(t, p):
	def structureCallback(mode, name, *fields):
		assert mode == 'call', mode
		
		fields = translateSymbolicFields(p, fields)
		s = datalogast.Structure(name, fields)
		p.addStructure(s)

	symbolEval(t, structureCallback)

def compileInputRelations(t, p):
	def tableCallback(mode, name, *fields):
		assert mode == 'call', mode
		
		fields = translateSymbolicFields(p, fields)
		r = datalogast.Relation(name, fields, 'input')
		p.addRelation(r)

	symbolEval(t, tableCallback)


def compileInternalRelations(t, p):
	def tableCallback(mode, name, *fields):
		assert mode == 'call', mode
	
		fields = translateSymbolicFields(p, fields)
		r = datalogast.Relation(name, fields, 'internal')
		p.addRelation(r)

	symbolEval(t, tableCallback)


def compileOutputRelations(t, p):
	def tableCallback(mode, name, *fields):
		assert mode == 'call', mode

		fields = translateSymbolicFields(p, fields)
		r = datalogast.Relation(name, fields, 'output')
		p.addRelation(r)

	symbolEval(t, tableCallback)

def processArgs(nodeCallback, leafCallback, args):
	outp = []
	for arg in args:
		if isinstance(arg, (list, tuple)):
			res = processArgs(nodeCallback, leafCallback, arg)
		else:
			res = leafCallback(arg)
		outp.append(res)
	return nodeCallback(outp)


def extractArgs(inp):
	return processArgs(tuple, lambda arg: arg.name, inp)

def checkArgs(name, fields, args):
	if len(fields) != len(args):
		raise datalogast.ExpressionArgumentError, "Expected %d arguments for %s:(%s), got %s" % (len(fields), name, str(fields), str(args))

	for (name, domain), arg in zip(fields, args):
		if isinstance(arg, (list, tuple)):
			assert isinstance(domain, datalogast.Structure), (domain, arg)
			checkArgs(name, domain.fields, arg)

def compileExpressions(f, p):
	def exprCallback(e):
		p.addExpression(e)

	def createTerm(mode, s, *args):
		if mode == 'call':
			if not s in p.symbols:
				raise datalogast.UnknownTableError, s

			relation = p.symbols[s]
			checkArgs(relation.name, relation.fields, args)
			term = datalogast.Term(relation, extractArgs(args))


		elif mode == '==':
			term = datalogast.Compare(s, mode, args[0])
		else:
			assert False, mode

		return TermWrapper([term], exprCallback)

	symbolEval(f, createTerm)

def astFromAlgorithim(Algorithim):
	p = datalogast.ProgramDescription()
	compileDomains(Algorithim.domains, p)

	assert p.domains, "No domains found."

	compileStructures(Algorithim.structures, p)

	compileInputRelations(Algorithim.inputRelations, p)
	compileInternalRelations(Algorithim.internalRelations, p)
	compileOutputRelations(Algorithim.outputRelations, p)

	assert p.relations, "No relations found."


	compileExpressions(Algorithim.expressions, p)

	for d in p.domains:
		for k, v in d.ops.iteritems():
			p.addRelation(v)

	for s in p.structures:
		for k, v in s.ops.iteritems():
			p.addRelation(v)

	
	assert p.expressions, "No expressions found."
	
	return p
