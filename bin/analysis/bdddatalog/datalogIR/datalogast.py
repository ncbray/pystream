class UnknownDomainError(Exception):
	pass

class UnknownTableError(Exception):
	pass

class SymbolRedefinitionError(Exception):
	pass

class ExpressionTypeError(Exception):
	pass

class ExpressionArgumentError(Exception):
	pass


class DatalogASTNode(object):
	__slots__ = ()

class Domain(DatalogASTNode):
	__slots__ = 'name', 'ops'
	def __init__(self, name):
		self.name = name
		self.ops = {}

	def __repr__(self):
		return self.name

	def getOp(self, op):
		if not op in self.ops:
			self.ops[op] = Relation(self.name+op+self.name, (('l', self),('r', self)), 'input')
		return self.ops[op]

class Structure(DatalogASTNode):
	__slots__ = 'name', 'fields', 'ops'
	def __init__(self, name, fields):
		assert isinstance(fields, (list, tuple))

		validateFields(fields)
		
		self.name = name
		self.fields = fields

		self.ops = {}

	def __repr__(self):
		fields = ", ".join([name+":"+str(domain) for name, domain in self.fields])
		return "%s(%s)" % (self.name, fields)

	# Code duplication bad?
	def getOp(self, op):
		if not op in self.ops:
			self.ops[op] = Relation(self.name+op+self.name, (('l', self),('r', self)), 'input')
		return self.ops[op]

def validateFields(fields):
	for name, type_ in fields:
		assert isinstance(type_, (Domain, Structure)), type_

class Relation(DatalogASTNode):
	__slots__ = 'name', 'fields', 'io'
	def __init__(self, name, fields, io):
		assert len(fields) > 0
		assert isinstance(fields, (list, tuple))
		assert io in ('input', 'output', 'internal')

		validateFields(fields)
		
		self.name = name
		self.fields = fields
		self.io = io

	def __repr__(self):
		fields = ", ".join([name+":"+str(domain) for name, domain in self.fields])
		return "%s(%s)" % (self.name, fields)

##class SubTerm(DatalogASTNode):
##	def __init__(self, args):
##		self.args  = tuple(args)

def argTuple(args):
	argStrs = []

	for arg in args:
		if isinstance(arg, (list, tuple)):
			argStrs.append(argTuple(arg))
		else:
			argStrs.append(str(arg))

	return "(%s)" % ", ".join(argStrs)

def validateTypes(name, fields, args, types):
	if not len(fields) == len(args):		
		raise ExpressionArgumentError, "Expected %d arguments for %s, got %s" % (len(fields), name, str(args))
	
	for (fname, ftype), arg in zip(fields, args):
		if isinstance(arg, (list, tuple)):
			assert isinstance(ftype, Structure), 'Bad expression: domain "%s" does not have subfields %s.' % (str(ftype), str(arg))
			validateTypes(name, ftype.fields, arg, types)
		else:
			assert isinstance(arg, str)
			
			if arg in types and types[arg] != ftype:
				raise ExpressionTypeError, "Expected %s would be %s, got %s" % (str(arg), repr(types[arg]), repr(ftype))

			if arg != '_':
				types[arg] = ftype

	return True

def collectSymbols(args):
	s = set()
	for arg in args:
		if isinstance(arg, (list, tuple)):
			s.update(collectSymbols(arg))
		else:
			assert isinstance(arg, str), arg
			s.add(arg)
	return s

def translateSymbols(lut, args):
	l = []
	for arg in args:
		if isinstance(arg, (list, tuple)):
			l.append(translateSymbols(lut, arg))
		else:
			assert isinstance(arg, str), arg
			l.append(lut.get(arg, arg))
	return tuple(l)

class Term(DatalogASTNode):
	def __init__(self, relation, args):
		assert len(args) > 0
		assert isinstance(relation, Relation)
		self.relation = relation
		self.__args  = tuple(args)
		
	def __repr__(self):
		return "%s%s" % (self.relation.name, argTuple(self.__args))

	def terms(self):
		return [self]

	def validateTypes(self, types):
		name = self.relation.name
		fields = self.relation.fields
		args = self.__args
		return validateTypes(name, fields, args, types)

		
	def translate(self, lut):
		return Term(self.relation, translateSymbols(lut, self.__args))

	def symbols(self):			
		return collectSymbols(self.__args)

	def args(self):
		return self.__args
	
	def relations(self, relations):
		relations.add(self.relation)

	def inversions(self, inv):
		pass

class Invert(DatalogASTNode):
	def __init__(self, term):
		self.term = term

	def validateTypes(self, types):
		return self.term.validateTypes(types)

	def relations(self, relations):
		self.term.relations(relations)

	def args(self):
		return self.term.args()

	def symbols(self):
		return self.term.symbols()

	def inversions(self, inv):
		self.relations(inv)

	def __repr__(self):
		return "~%s" % repr(self.term)

class Compare(DatalogASTNode):
	def __init__(self, left, op, right):
		assert isinstance(left, str)
		assert isinstance(right, str)
		assert left != right, "Cannot handle constant equalities."

		self.left = left
		self.op = op
		self.right = right

		self.type = None
		self.relation = None

	def setType(self, t):
		self.type = t
		self.relation = t.getOp(self.op)

	def relations(self, relations):
		assert self.relation
		relations.add(self.relation)

	def inversions(self, inv):
		pass

	def args(self):
		return (self.left, self.right)

	def symbols(self):
		return set(self.args())
		
	def validateTypes(self, types):
		l = types.get(self.left, None)
		r = types.get(self.right, None)

		if l:
			if r:
				if l != r:
					raise ExpressionTypeError, "Expected %s would be %s, got %s" % (str(self.right), repr(l), repr(r))				

				self.setType(l)
				return True
			else:
				types[self.right] = l
				self.setType(l)
				return True
		else:
			if r:
				types[self.left] = r
				self.setType(r)
				return True
			else:
				return False

			

	def __repr__(self):
		return "%s%s%s" % (repr(self.left), self.op, repr(self.right))

def reprMulti(terms):
	return ", ".join([repr(term) for term in terms])

def validateExprTypes(target, terms):
	# Make sure there's no inconsistancy with symbols.
	
	types = {}

	complete = False

	# May take a few iterations to resolve operators.
	# A worklist would be more efficient, but who cares?
	while not complete:
		complete = True
		complete &= target.validateTypes(types)
		for term in terms:
			complete &= term.validateTypes(types)

def checkCollapsingTarget(target):
	args = filter(lambda a: a != '_', target.args())
	assert len(args) == len(set(args)), "Can't deal with a collapsing target, yet: %s" % str(target)


class Expression(DatalogASTNode):
	__slots__ = 'target', 'terms'
	def __init__(self, target, terms):
		assert isinstance(target, Term)
		assert isinstance(terms, (list, tuple)), type(terms)
		assert not target.relation.io is 'input'
		checkCollapsingTarget(target)

		terms = list(terms)

		validateExprTypes(target, terms)
			

		self.target = target
		self.terms  = terms



	def __repr__(self):
		return "%s :- %s." % (repr(self.target), reprMulti(self.terms))


	def dependancies(self):
		reads = set()
		for term in self.terms:
			term.relations(reads)
			
		return self.target.relation, reads

	def translate(self, lut):
		return Expression(self.target.translate(lut), [t.translate(lut) for t in self.terms])

	def symbols(self):
		s = self.target.symbols()
		for term in self.terms:
			s.update(term.symbols())
		return s

	def inversions(self):
		inv = set()
		self.target.inversions(inv)
		assert not inv
		for term in self.terms:
			term.inversions(inv)
		return inv

class ProgramDescription(object):
	def __init__(self):
		self.domains = []
		self.structures = []
		self.relations  = []
		self.expressions = []
		self.symbols = {}
		
	def addDomain(self, domain):
		self.domains.append(domain)
		self.addSymbol(domain.name, domain)

	def addStructure(self, structure):
		self.structures.append(structure)
		self.addSymbol(structure.name, structure)

	def addRelation(self, relation):
		self.relations.append(relation)
		self.addSymbol(relation.name, relation)

	def addExpression(self, e):
		self.expressions.append(e)

	def addSymbol(self, name, value):
		if name in self.symbols:
			raise SymbolRedefinitionError, "Tried to redefine %s from %s to %s" % (name, self.symbols[name], value)
		assert not name in self.symbols
		self.symbols[name] = value

	def dump(self):
		print "DOMAINS"
		for d in self.domains:
			print "\t", d
		print

		print "STRUCTURES"
		for s in structures:
			print "\t", s
		print

		print "RELATIONS"
		for t in self.relations:
			print "\t", t
		print

		print "EXPRESSIONS"
		for e in self.expressions:
			print "\t", e
		print

	def regenerateSymbolTable(self):
		self.symbols = {}

		for domain in self.domains:
			self.addSymbol(domain.name, domain)

		for structure in self.structures:
			self.addSymbol(structure.name, structure)

		for relation in self.relations:
			self.addSymbol(relation.name, relation)
			
