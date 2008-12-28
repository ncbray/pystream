# Patterned after "Visitor Combination and Traversal Control" by J.M.W. Visser, 2001

# This modules allows the creation and composition of algorithims for
# processing directed graphs.

class VisitFailiure(Exception):
	pass

# Abstract base class.
class Traversal(object):
	def setObjectModel(self, om, visited=None):
		if not visited:
			visited = set()

		if not self in visited:
			visited.add(self)
			self.om = om
			for child in self.iterchildren():
				child.setObjectModel(om, visited)

	def children(self):
		return ()

	def iterchildren(self):
		return iter(self.children())

class Identity(Traversal):
	def visit(self, node, args):
		return node


class Sequence(Traversal):
	def __init__(self, *children):
		self._children = tuple(children)

	def visit(self, node, args):
		for child in self._children:
			child.visit(node, args)

	def children(self):
		return self._children


class Fail(Traversal):
	def visit(self, node, args):
		raise VisitFailiure

class Not(Traversal):
	def __init__(self, child):
		self.child = child
		
	def visit(self, node, args):
		try:
			self.child.visit(node, args)
		except VisitError:
			pass
		else:
			raise VisitError

	def children(self):
		return (self.child,)

# TODO if then else  Choice(Sequence(if, then), else)? (not quite right if then can bomb)
class Choice(Traversal):
	def __init__(self, *children):
		self._children = tuple(children)

	def visit(self, node, args):
		for child in self._children:
			try:
				return child.visit(node, args)
			except VisitFailiure:
				pass
		raise VisitFailiure

	def children(self):
		return self._children

# TODO non-determanistic choice as type?  Allows compiler optimization?
def Nondetermanistic(*children):
	return Choice(*children)

			
class AllChildren(Traversal):
	def __init__(self, visitor):
		self.visitor = visitor
		
	def visit(self, node, args):
		return [self.visitor.visit(child, args) for child in self.om.iterchildren(node)]

	def children(self):
		return (self.visitor,)


class AnyChild(Traversal):
	def __init__(self, visitor):
		self.visitor = visitor
		
	def visit(self, node, args):
		for child in self.om.iterchildren(node):
			try:
				return self.visitor.visit(child, args)
			except VisitFailiure:
				pass
		raise VisitFailiure
			
	def children(self):
		return (self.visitor,)


class Repeat(Traversal):
	def __init__(self, visitor):
		self.visitor = visitor

	def visit(self, node, args):
		try:
			while True:
				self.visitor.visit(node, args)
		except VisitFailiure:
			pass

	def children(self):
		return (self.visitor,)


class Innermost(Sequence):
	def __init__(self, s):
		Sequence.__init__(self, AllChildren(self), Try(s, self))
		
#	innermost(s) = all(innermost(s)); try(s; innermost(s))

# Composites

##class TopDown(Sequence):
##	def __init__(self, visitor):
##		Sequence.__init__(self, visitor, AllChildren(self))
##
class BottomUp(Sequence):
	def __init__(self, visitor):
		Sequence.__init__(self, AllChildren(self), visitor)
##
##class PrePost(Sequence):
##	def __init__(self, pre, post):
##		Sequence.__init__(self, Sequence(pre, AllChildren(self)), post)

class Memoize(Sequence):
	def __init__(self, visitor):
		self.visitor = visitor
		self.visited = set()

	def visit(self, node, args):
		if not node in self.visited:
			self.visited.add(node)
			self.visitor.visit(node, args)

	def children(self):
		return (self.visitor,)

class DFS(Traversal):
	def __init__(self, pre, post):
		self.pre = pre
		self.post = post
		self.visited = set()

	def children(self):
		return (self.pre, self.post)

	# DFS using the main stack.  An "internal" stack would be better.
	def visit(self, node, args):
		if node != None and not isinstance(node, (tuple, list)):
			if node in self.visited:
				return
			else:
				self.visited.add(node)
		
		self.pre.visit(node, args)			
		for child in self.om.iterchildren(node):
			self.visit(child, args)
		self.post.visit(node, args)

###################################################
### Object model: how do we traverse the nodes? ###
###################################################

class ObjectModel(object):
	def children(self, node):
		raise NotImplemented

	def iterchildren(self, node):
		return iter(self.children(node))

	def disbatch(self, visitor, node, args):
		raise NotImplemented

class DefaultObjectModel(ObjectModel):
	def children(self, node):
		if hasattr(node, 'children'):
			children = node.children()
			return children
		elif isinstance(node, (list, tuple)):
			return node
		else:
			return ()

	def disbatch(self, visitor, node, args):
		return node.accept(visitor, *args)


class Reversed(ObjectModel):
	def __init__(self, om):
		self.om = om

	def children(self, node):
		return tuple(self.iterchildren(node))

	def iterchildren(self, node):
		return reversed(self.om.children(node))

	def disbatch(self, visitor, node, args):
		return self.om.disbatch(visitor, node, args)


###############################
### The leaf of the visitor ###
###############################

class ConcreteVisitor(Traversal):
	def visit(self, node, args):
		return self.om.disbatch(self, node, args)


