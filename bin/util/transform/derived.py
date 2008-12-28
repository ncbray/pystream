from base import *
from . generictraversal import All
from . pattern import Match, Build

# TODO make derived - requires better scope/transform support.
# {x:?x;s;!x}
class Where(Transformer):
	__metaclass__ = astnode
	__fields__    = 's', 
	__types__     = {'s':Transformer}
	
	def __call__(self, node, env):
		self.s(node, env)
		return node


def ITE(cond, t, f):
	return Conditional(Where(cond), t, f)

def Try(s):
	return Determanistic([s, identity])

@recursive
def BottomUpT(r, s, t):
	return Sequence([t(r), s])	

def BottomUp(s):
	return BottomUpT(s, All)

@recursive
def InnermostT(r, s, t):
	return Sequence([t(r), Try(Sequence([s, r]))])

def Innermost(s):
	return InnermostT(s, All)


@recursive
def AllTD(r, s):
	return Determanistic([s, All(r)])


def getVarsR(node, s):
	if isinstance(node, Symbol):
		s.add(node.name)
	else:
		for child in children(node):
			getVarsR(child, s)

def getVars(*nodes):
	s = set()
	for node in nodes:
		getVarsR(node, s)
	return frozenset(s)

def Rewrite(l, r, s=None):
	m = Match(l)
	b = Build(r)
	if s == None:
		#v = Vars(l, r)
		scopevars = getVars(m, b)
		return Scope(scopevars, Sequence([m,b]))
	else:
		#v = Vars(l, r, s)
		w = Where(s)
		scopevars = getVars(m, w, b)
		return Scope(scopevars, Sequence([m,w,b]))

# s => p
# TODO is there where wrapper correct?
def MatchIntoPattern(s, p):
	assert isinstance(s, Transformer), s
	return Where(Sequence([s, Match(p)]))

# <s> p
def ApplyToPattern(s, p):
	assert isinstance(s, Transformer), s
	return Sequence([Build(p), s])

#Idiom <s> t => t'

def Do(s):
	assert isinstance(s, Transformer), s	
	return Call(s, ())


# TODO implement context[] operators?
# e* for arbitrary number of arguments in pattern?

# Repeat - rec x(try(s; x))
