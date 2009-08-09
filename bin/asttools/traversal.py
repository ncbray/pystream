__all__ = ['allChildren', 'allChildrenReversed',
	'replaceAllChildren', 'replaceAllChildrenReversed',
	'visitAllChildren', 'visitAllChildrenForced', 'visitAllChildrenArgs',
	'visitAllChildrenReversed']

from . metaast import ASTNode

ListTypes = (list, tuple)

# Performance critical
def allChildren(s, node, clone=False):
	if isinstance(node, ASTNode):
		# AST node
		if node.__shared__:
			# Shared nodes are not traversed
			assert not clone, node
			return node

		# Unshared nodes a rewritten
		children = node.children()

		newchildren = []
		changed     = clone

		for child in children:
			newchild = s(child)
			newchildren.append(newchild)
			if newchild is not child:
				changed = True

		if changed:
			newnode = type(node)(*newchildren)
			newnode.annotation = node.annotation
			return newnode
		else :
			return node

	elif isinstance(node, list):
		# List
		children = node

		newchildren = []
		changed     = clone

		for child in children:
			newchild = s(child)
			newchildren.append(newchild)
			if newchild is not child:
				changed = True

		if changed:
			return newchildren
		else:
			return node

	elif isinstance(node, tuple):
		# List
		children = node

		newchildren = []
		changed     = clone

		for child in children:
			newchild = s(child)
			newchildren.append(newchild)
			if newchild is not child:
				changed = True

		if changed:
			return tuple(newchildren)
		else:
			return node

	else:
		# Other
		return node

def allChildrenReversed(s, node):
	if isinstance(node, ASTNode):
		# AST node
		if node.__shared__:
			# Shared nodes are not traversed
			assert not clone, node
			return node

		# Unshared nodes a rewritten
		children = node.children()

		newchildren = []
		changed     = False

		for child in reversed(children):
			newchild = s(child)
			newchildren.append(newchild)
			if newchild is not child:
				changed = True

		if changed:
			newchildren.reverse()
			newnode = type(node)(*newchildren)
			newnode.annotation = node.annotation
			return newnode
		else :
			return node

	elif isinstance(node, list):
		# List
		children = node

		newchildren = []
		changed     = False

		for child in reversed(children):
			newchild = s(child)
			newchildren.append(newchild)
			if newchild is not child:
				changed = True

		if changed:
			newchildren.reverse()
			return newchildren
		else:
			return node

	elif isinstance(node, tuple):
		# List
		children = node

		newchildren = []
		changed     = False

		for child in reversed(children):
			newchild = s(child)
			newchildren.append(newchild)
			if newchild is not child:
				changed = True

		if changed:
			newchildren.reverse()
			return tuple(newchildren)
		else:
			return node

	else:
		# Other
		return node

def replaceAllChildren(s, node):
	if isinstance(node, ASTNode):
		assert node.__shared__, node
		node.replaceChildren(*[s(child) for child in node.children()])
		return node
	else:
		assert False, node

def replaceAllChildrenReversed(s, node):
	if isinstance(node, ASTNode):
		assert node.__shared__, node
		newchildren = [s(child) for child in reversed(node.children())]
		newchildren.reverse()
		node.replaceChildren(*newchildren)
		return node
	else:
		assert False, node

# Visit - no return value

def visitAllChildren(s, node):
	if isinstance(node, ASTNode):
		if node.__shared__: return
		for child in node.children():
			s(child)
	elif isinstance(node, ListTypes):
		for child in node:
			s(child)
	else:
		pass

def visitAllChildrenForced(s, node, *args):
	if isinstance(node, ASTNode):
		for child in node.children():
			s(child, *args)
	elif isinstance(node, ListTypes):
		for child in node:
			s(child, *args)
	else:
		pass

def visitAllChildrenArgs(s, node, *args):
	if isinstance(node, ASTNode):
		if node.__shared__: return
		for child in node.children():
			s(child, *args)
	elif isinstance(node, ListTypes):
		for child in node:
			s(child, *args)
	else:
		pass

def visitAllChildrenReversed(s, node):
	if isinstance(node, ASTNode):
		if node.__shared__: return
		for child in reversed(node.children()):
			s(child)
	elif isinstance(node, ListTypes):
		for child in reversed(node):
			s(child)
	else:
		pass