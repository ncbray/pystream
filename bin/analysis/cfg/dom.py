from util.graphalgorithim import dominator

class DJNode(object):
	__slots__ = 'node', 'idom', 'level', 'd', 'j', 'marked', 'idf', 'pre', 'post'
	def __init__(self, node):
		self.node = node
		self.idom = None
		self.d	= []
		self.j	= []
		self.marked = False
		#self.reset()

		self.idf = set()

##	def reset(self):
##		self.visited = False
##		self.alpha   = False
##		self.inPhi   = False
##		self.next	= None

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

class MakeDJGraph(object):
	def __init__(self, idom, forwardCallback, bindCallback):
		self.idom = idom
		self.processed = set()
		self.nodes = {}
		self.numLevels = 0
		self.uid = 0
		self.forwardCallback = forwardCallback
		self.bindCallback = bindCallback

	def getNode(self, g):
		if g not in self.nodes:
			result = DJNode(g)
			self.bindCallback(g, result)
			self.nodes[g] = result

			idom = self.idom[g]
			if idom is not None:
				result.setIDom(self.getNode(idom))
				self.numLevels = max(self.numLevels, result.level)
			else:
				result.level = 0
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


class Bank(object):
	def __init__(self, numLevels):
		self.levels = [None for i in range(numLevels)]
		self.current = numLevels-1

	def insertNode(self, node):
		assert node.next is None
		node.next = self.levels[node.level]
		self.levels[node.level] = node

	def getNode(self):
		i = self.current

		while i >= 0:
			djnode = self.levels[i]
			if djnode is not None:
				assert djnode.level == i

				self.levels[i] = djnode.next
				self.current = i
				return djnode
			else:
				i -= 1
		return None

class PlacePhi(object):
	def __init__(self, na, numLevels):
		self.bank = Bank(numLevels)

		for djnode in na:
			djnode.alpha = True
			self.bank.insertNode(djnode)

		self.idf = []
		self.main()

	def main(self):
		current = self.bank.getNode()
		while current:
			print "MAIN", current.node, current.level
			self.currentLevel = current.level
			self.visit(current)
			current = self.bank.getNode()


	def visit(self, djnode):
		if djnode.visited:
			print "skip", djnode.node
			return
		djnode.visited = True

		for j in djnode.j:
			if j.level <= self.currentLevel:
				if not j.inPhi:
					j.inPhi = True
					self.idf.append(j)
					if not j.alpha:
						self.bank.insertNode(j)

		for d in djnode.d:
			self.visit(d)

# Note that this doesn't actually find the entire dominance frontier,
# just the closest merges.
# loose upper bound -> O(|E|*depth(DJTree))
class FullIDF(object):
	def __init__(self):
		self.stack = []

	def process(self, node):
		assert node.level == len(self.stack)
		self.stack.append(node)

		for d in node.d:
			self.process(d)

		for j in node.j:
			if j.level <= node.level:
				for i in range(j.level, node.level+1):
					self.stack[i].idf.add(j)

		self.stack.pop()


def evaluate(roots, forwardCallback, bindCallback):
	idoms = dominator.findIDoms(roots, forwardCallback)
	mdj   = MakeDJGraph(idoms, forwardCallback, bindCallback)
	djs    = [mdj.process(root) for root in roots]

	uid = 0
	for dj in djs:
		uid = dj.number(uid)

	fidf = FullIDF()
	for dj in djs: fidf.process(dj)

	return djs
