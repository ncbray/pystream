from programIR.base.metaast import astnode, Symbol

class TransformationFailiure(Exception):
	pass

class Transformer(object):
	__slots__ = ()
	
	def transform(self, node, env):
		newnode = self(node, env)
		#if newnode == fail: raise TransformationFailiure
		return newnode

	def __call__(self, node, env):
		raise NotImplementedError

class Identity(Transformer):
	__metaclass__ = astnode
	__fields__    = ()
	
	def __call__(self, node, env):
		assert node != fail, repr(self)
		return node

	def __repr__(self):
		return 'id'

class Fail(Transformer):
	__metaclass__ = astnode
	__fields__    = ()

	def __call__(self, node, env):
		assert node != fail, repr(self)
		return doFail()

	def __repr__(self):
		return 'fail'

identity = Identity()
fail = Fail()


def doFail():
	raise TransformationFailiure
	#return fail




class Sequence(Transformer):
	__metaclass__ = astnode
	__fields__    = 'strategies'
	__types__     = {'strategies':list}

	def __init__(self, strategies):
		newstrategies = []
		for s in strategies:
			if isinstance(s, Sequence):
				newstrategies.extend(s.strategies)
			else:
				newstrategies.append(s)

		self.strategies = newstrategies
	
	def __call__(self, node, env):
		assert node != fail, repr(self)

		for s in self.strategies:
			node = s(node, env)

		return node



class Choice(Transformer):
	__metaclass__ = astnode
	__fields__    = 'strategies'
	__types__     = {'strategies':list}

	def __init__(self, strategies):
		newstrategies = []
		for s in strategies:
			if isinstance(s, Choice):
				newstrategies.extend(s.strategies)
			else:
				newstrategies.append(s)

		self.strategies = newstrategies

##	def __call__(self, node, env):
##		assert node != fail, repr(self)
##		
##		newnode = node
##		
##		for s in self.strategies:
##			assert s != None, self.strategies
##			newnode = s(node, env)
##			if newnode != fail: break
##
##		return newnode

	def __call__(self, node, env):
		assert node != fail, repr(self)
		
		newnode = node
		
		for s in self.strategies:
			try:
				return s(node, env)
			except TransformationFailiure:
				pass
			
		raise TransformationFailiure

class TypeDispatch(Transformer):
	__metaclass__ = astnode
	__fields__    = 'dispatch'
	__types__     = {'dispatch':dict}

	def __call__(self, node, env):
		s = self.dispatch.get(type(node), fail)
		return s(node, env)

def Determanistic(args):
	return Choice(args)


class Conditional(Transformer):
	__metaclass__ = astnode
	__fields__    = 'cond', 't', 'f'
	__types__     = {'cond':Transformer, 't':Transformer, 'f':Transformer}


	def __call__(self, node, env):
		try:
			newnode = self.cond(node, env)
		except TransformationFailiure:
			return self.f(node, env)
		else:
			return self.t(newnode, env)

# TODO mask variables?
class Scope(Transformer):
	__metaclass__ = astnode
	__fields__    = 'vars', 's'
	__types__     = {'vars':frozenset, 's':Transformer}

	def __call__(self, node, env):
##		for var in self.vars:
##			assert not env.contains(var), (var, self)
			
		newenv = env.new()
		result = self.s(node, newenv)
		return result


class Call(Transformer):
	__metaclass__ = astnode
	__fields__    = 'function', 'strategies', 'patterns'
	__types__     = {'strategies':list, 'patterns':list}

class Recursive(Transformer):
	__metaclass__ = astnode
	__fields__    = 's', 
	__types__     = {'s':Transformer}
	__optional__  = 's'

	def __call__(self, node, env):
		newenv = env.new()
		return self.s(node, newenv)

	def __repr__(self):
		return "Recursive(...)"

	def bind(self, s):
		self.s = s

# A wrapper function to help making recursive strategies.
def recursive(f):
	def recursiveWrap(*args):
		r = Recursive(None)
		s = f(r, *args)
		r.bind(s)
		return r
	return recursiveWrap



class TransformWrapper(Transformer):
	__metaclass__ = astnode
	__fields__    = ()
	__slots__     = 'f'

	def __init__(self, f):
		self.f = f
		
	def __call__(self, node, env):
		return self.f(node, env)

def transformer(f):
	return TransformWrapper(f)

##class Var(Transformer):
##	__metaclass__ = astnode
##	__fields__    = 'name'
##	__types__     = {'name':str}
##
##	def __call__(self, node, env):
##		value = env.read(self.name)
##		return value(node, env)
