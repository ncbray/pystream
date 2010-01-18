from . import dominator

class DJNode(object):
	__slots__ = 'node', 'idom', 'level', 'd', 'j', 'pre', 'post'
	def __init__(self, node):
		self.node = node
		self.idom = None
		self.d	= []
		self.j	= []

	def setIDom(self, idom):
		self.idom  = idom
		self.level = idom.level + 1
		self.idom.d.append(self)

	def number(self, uid):
		self.pre = uid
		uid += 1

		for d in self.d:
			uid = d.number(uid)

		self.post = uid
		uid += 1

		return uid

	# Faster than traversing idom?
	def dominates(self, other):
		return self.pre <= other.pre and self.post >= other.post

	def __repr__(self):
		return "dj(%r)" % self.node

class MakeDJGraph(object):
	def __init__(self, idom, forwardCallback, bindCallback):
		self.idom = idom
		self.processed = set()
		self.nodes = {}
		self.numLevels = 0
		self.uid = 0
		self.forwardCallback = forwardCallback
		self.bindCallback = bindCallback

		self.roots = []

	def getNode(self, g):
		if g not in self.nodes:
			result = DJNode(g)
			self.bindCallback(g, result)
			self.nodes[g] = result

			idom = self.idom[g]

			if idom is not None:
				result.setIDom(self.getNode(idom))
			else:
				result.level = 0
				self.roots.append(result)

			self.numLevels = max(self.numLevels, result.level+1)
		else:
			result = self.nodes[g]
		return result

	def process(self, node):
		if node not in self.processed:
			self.processed.add(node)

			djnode = self.getNode(node)

			for child in self.forwardCallback(node):
				djchild = self.process(child)

				if djchild.idom is not djnode:
					djnode.j.append(djchild)

			return djnode
		else:
			return self.getNode(node)

def dummyBind(node, djnode):
	pass

def makeFromIDoms(roots, idom, forwardCallback, bindCallback=None):
	if bindCallback is None: bindCallback = dummyBind

	mdj = MakeDJGraph(idom, forwardCallback, bindCallback)
	for root in roots:
		mdj.process(root)

	djs = mdj.roots

	uid = 0
	for dj in djs: uid = dj.number(uid)

	return djs

def make(roots, forwardCallback, bindCallback=None):
	if bindCallback is None: bindCallback = dummyBind
	idoms = dominator.findIDoms(roots, forwardCallback)
	return makeFromIDoms(roots, idoms, forwardCallback, bindCallback)
