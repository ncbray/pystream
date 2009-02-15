from base import *

### Generic traversal ###

def identicalChildren(oldchildren, newchildren):
	#return False
	return len(oldchildren) == len(newchildren) and all(map(lambda (a,b): id(a) == id(b), zip(oldchildren, newchildren)))

def isShared(node):
	#return hasattr(node, '__shared__') and node.__shared__
	return getattr(node, '__shared__', False)


def allChildren(s, node, clone=False):
	if isShared(node):
		assert not clone
		return node

	oldchildren = children(node)
	newchildren = [s(child) for child in oldchildren]

	if identicalChildren(oldchildren, newchildren) and not clone:
		return node
	else:
		return reconstruct(node, newchildren)


def visitAllChildren(s, node):
	if isShared(node):
		return

	for child in children(node):
		s(child)

def allChildrenReversed(s, node):
	if isShared(node):
		return node

	oldchildren = list(reversed(children(node)))
	newchildren = [s(child) for child in oldchildren]

	if identicalChildren(oldchildren, newchildren):
		return node
	else:
		newchildren.reverse()
		return reconstruct(node, newchildren)

def visitAllChildrenReversed(s, node):
	if isShared(node):
		return

	for child in reversed(children(node)):
		s(child)



### Compound strategies ###


class Innermost(object):
	def __init__(self, strategy):
		self.strategy = strategy
		self.canonical = set()

	def __call__(self, node):
		if id(node) in self.canonical:
			return node

		while True:
			node = allChildren(self, node)
			try:
				node = self.strategy(node)
			except TransformFailiure:
				self.canonical.add(id(node))
				return node

class TopDown(object):
	def __init__(self, strategy):
		self.strategy = strategy

	def __call__(self, node):
		node = self.strategy(node)
		node = allChildren(self, node)
		return node

class BottomUp(object):
	def __init__(self, strategy):
		self.strategy = strategy

	def __call__(self, node):
		node = allChildren(self, node)
		node = self.strategy(node)
		return node

class DownUp(object):
	def __init__(self, down, up):
		self.down = down
		self.up = up

	def __call__(self, node):
		node = self.down(node)
		node = allChildren(self, node)
		node = self.up(node)
		return node


class Try(object):
	def __init__(self, strategy):
		self.strategy = strategy

	def __call__(self, node):
		try:
			node = self.strategy(node)
		except TransformFailiure:
			pass

		return node
