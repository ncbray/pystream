# Used for maching call signatures to function signatures.

class FunctionSignature(object):
	def __init__(self, args, numdefaults, vargs, kargs):
		self.args 		= tuple(args)
		self.numdefaults 	= numdefaults
		self.vargs 		= vargs
		self.kargs		= kargs

	def minargs(self):
		return len(self.args)-self.numdefaults

	def maxpos(self):
		if self.vargs:
			return -1
		else:
			return len(self.args)
		
	def maxkwd(self):
		if self.kargs:
			return -1
		else:
			return len(self.args)

	def maxargs(self):
		if self.vargs or self.kargs:
			return -1
		else:
			return len(self.args)

	def __eq__(self, other):
		return type(self) == type(other) and self.args == other.args and self.numdefaults == other.numdefaults and self.vargs == other.vargs and self.kargs == other.kargs

	def __hash__(self):
		return hash(self.args) ^ hash(self.numdefaults) ^ hash(self.vargs) ^ hash(self.kargs)

class CallSignature(object):
	def __init__(self, numpos, kwds, vargs, kargs):
		self.numpos = numpos
		self.kwds 	= kwds
		self.vargs 	= vargs
		self.kargs 	= kargs

	def __eq__(self, other):
		return type(self) == type(other) and self.numpos == other.numpos and self.kwds == other.kwds and self.vargs == other.vargs and self.kargs == other.kargs

	def __hash__(self):
		return hash(self.numpos) ^ hash(self.kwds) ^ hash(self.vargs) ^ hash(self.kargs)




from programIR.python.ast import isPythonAST

# HACK global cache
sigcache = {}

def getFunctionSignature(ast):
	# HACK assumes no default arguments

	sig = FunctionSignature(ast.code.argnames, 0, bool(ast.code.vargs), bool(ast.code.kargs))

	# Only keep one copy.
	if not sig in sigcache:
		sigcache[sig] = sig
		
	return sigcache[sig]

def gatherSignatures(desc):
	for ast in desc.functions:
		if isPythonAST(ast):
			sig = getFunctionSignature(ast)
		else:
			pass # TODO support low-level asts?
		
		# What to do now?