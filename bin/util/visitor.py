import compiler

#class StandardWalker(compiler.visitor.ASTVisitor):
class StandardWalker(object):
	__slots__ = '_cache', 'default', 'visitor'
	
	def __init__(self, visitor):
		self._cache = {}

		self.visitor = visitor
		visitor.visit = self.dispatch

		self.default = self.getDefault()

	def walkerDefault(self, node, *args):
		for child in node.getChildNodes():
			self.dispatch(child, *args)
	
	def getDefault(self):
		# API change, allow the visitor to spesify the default.
		if hasattr(self.visitor, 'default') and callable(self.visitor.default):
			return self.visitor.default
		else:
			return self.walkerDefault

	def cacheType(self, node):
		klass = node.__class__
		meth = getattr(self.visitor, 'visit'+klass.__name__, self.default)
		self._cache[klass] = meth
		return meth
	
	def dispatchkargs(self, node, *args, **kargs):
		meth = self._cache.get(node.__class__)
		
		if meth is None:
			meth = self.cacheType(node)
			
		return meth(node, *args, **kargs)

	def preorderkargs(self, tree, visitor, *args, **kargs):
		"""Do preorder walk of tree using visitor"""
		self.visitor = visitor
		self.default = self.getDefault()

		visit = self.dispatch
		
		visitor.visit = visit
		# API change, return the result of the walk.
		return visit(tree, *args, **kargs) # XXX *args make sense?

	def dispatch(self, node, *args):
		meth = self._cache.get(node.__class__)
		if meth is None: meth = self.cacheType(node)
		return meth(node, *args)

	def preorder(self, tree, visitor, *args):
		"""Do preorder walk of tree using visitor"""
		# API change, return the result of the walk.
		return self.dispatch(tree, *args) # XXX *args make sense?


_walker = StandardWalker
def walk(tree, visitor, args=(), walker=None, verbose=None):
	if walker is None: walker = _walker(visitor)
	if verbose is not None: walker.VERBOSE = verbose
	# API change, does not return the visitor
	# (it was passed as an argument, so why bother?)
	return walker.preorder(tree, visitor, *args)


##class StandardVisitor(object):
##	__slots__ = 'visit'
##
##	def __init__(self):
##		StandardWalker(self)
##
##	def default(self, block, *args):
##		raise NotImplementedError, "%s -> %s:%s" % (self.__class__.__name__, type(block).__name__, repr(block))
##
##	def walk(self, tree, *args):
##		# Not initalized correctly?
##		if not hasattr(self, 'visit'):
##			StandardWalker(self)
##		
##		return self.visit(tree, *args)


class StandardVisitor(object):
	__slots__ = '__cache'

	def __init__(self):
		self.__cache = {}
##		StandardWalker(self)

	def default(self, block, *args):
		raise NotImplementedError, "%s -> %s:%r" % (type(self).__name__, type(block).__name__, block)

	def walk(self, tree, *args):
		# Not initalized correctly?
		if not hasattr(self, '__cache'):
			self.__cache = {}
		return self.visit(tree, *args)

	def __cacheType(self, node):
		cls = type(node)
		meth = getattr(self, 'visit'+cls.__name__, self.default)
		self.__cache[cls] = meth
		return meth
	
	def visit(self, node, *args):
		meth = self.__cache.get(node.__class__)
		if meth is None:
			meth = self.__cacheType(node)
		return meth(node, *args)


class TracingVisitor(StandardVisitor):
	__slots__ = '__indent', 'trace'

	def __init__(self):
		StandardVisitor.__init__(self)
		self.__indent = 0
		self.trace = False

	def visit(self, node, *args):
		if self.trace:
			print "%strace %s" % (self.__indent*'\t', str(type(node).__name__))

		self.__indent += 1
		result = StandardVisitor.visit(self, node, *args)
		self.__indent -= 1

		return result
