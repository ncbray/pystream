__all__ = ['allChildren', 'replaceAllChildren',
	'visitAllChildren', 'visitAllChildrenArgs',
	'allChildrenReversed', 'visitAllChildrenReversed']

from asttools.metaast import children, reconstruct

def identicalChildren(oldchildren, newchildren):
	return len(oldchildren) == len(newchildren) and all(map(lambda (a,b): id(a) == id(b), zip(oldchildren, newchildren)))

def isShared(node):
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

def replaceAllChildren(s, node):
	assert isShared(node), type(node)

	oldchildren = children(node)
	newchildren = [s(child) for child in oldchildren]

	node.replaceChildren(*newchildren)
	return node


def visitAllChildren(s, node):
	if isShared(node):
		return

	for child in children(node):
		s(child)

def visitAllChildrenArgs(s, node, *args):
	if isShared(node):
		return

	for child in children(node):
		s(child, *args)

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
