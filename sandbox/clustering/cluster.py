import math
import random
import time

# Enthropy function.
def h(p):
	if p <= 0.0 or p >= 1.0:
		return 0.0
	else:
		return -p*math.log(p)-(1.0-p)*math.log(1.0-p)


def calculatePartialH(c1, c2, numEdges):
	prod = c1*c2
	return prod*h(numEdges/(2.0*prod))

# Metropolis-Hastings accept.
def accept(delta, explore):
	return delta >= 0.0 or math.exp(delta/explore) >= random.random()




class TreeBase(object):
	__slots__ = 'parent'
	def values(self):
		s = set()
		self.gatherValues(s)
		return s

class Leaf(TreeBase):
	__slots__ = 'value'
	def __init__(self, value):
		self.parent 	= None
		self.value 	= value

	def leafCount(self):
		return 1

	def recount(self):
		pass

	def classify(self, a, b, c, cache):
		# Is the parent a or b or c?

		if self in cache:
			current = cache[self]
		else:
			current = self

		while current != None:
			if current == a:
				cache[self] = current
				return 0
			elif current == b:
				cache[self] = current
				return 1
			elif current == c:
				cache[self] = current
				return 2
			else:
				current = current.parent
		assert False, (self.value)

	def trace(self):
		t = [self]
		current = self.parent
		while current:
			t.insert(0, current)
			current = current.parent
		return t

	def dump(self, tabs):
		print "%s%s" % (tabs, str(self.value))

	def __repr__(self):
		return repr(self.value)

	def calcDecendantLogL(self):
		return 0.0

	def gatherValues(self, s):
		s.add(self.value)

class Node(TreeBase):
	__slots__ = 'left', 'right', 'edges', 'count'

	def __init__(self, left, right):
		self.parent 	= None
		self.left 	= left
		self.right 	= right

		self.edges = []

		self.recount()

	def addEdge(self, e):
		e.next = self.edges
		self.edges = e

	def recount(self):
		self.left.parent = self
		self.right.parent = self
		self.count = self.left.leafCount()+self.right.leafCount()


	def leafCount(self):
		return self.count

	def dump(self, tabs):
		print "%s%f / %f" % (tabs, self.calcP(), -self.calcDecendantLogL())
		print tabs, self.edges
		#print tabs, self.calcP()
		tabs += '\t'
		self.left.dump(tabs)
		self.right.dump(tabs)

	def calcP(self):
		return len(self.edges)/(2.0*self.left.leafCount()*self.right.leafCount())

	def calcPartialLogL(self):
		return calculatePartialH(self.left.leafCount(), self.right.leafCount(), len(self.edges))

	def calcDecendantLogL(self):
		logl = self.calcPartialLogL()
		logl += self.left.calcDecendantLogL()
		logl += self.right.calcDecendantLogL()
		return logl

	def gatherValues(self, s):
		self.left.gatherValues(s)
		self.right.gatherValues(s)


class Edge(object):
	__slots__ = 'a', 'b', 'next'

	def __init__(self, a, b):
		self.a = a
		self.b = b
		self.next = None

	def __repr__(self):
		return "e(%s, %s)" % (repr(self.a), repr(self.b))

def classifyEdge(e):
	at = e.a.trace()
	bt = e.b.trace()

	for ap, bp in zip(at, bt):
		if ap != bp:
			assert ap.parent == bp.parent
			return ap.parent
	assert False


def addEdge(a, b):
	e = Edge(a, b)
	at = a.trace()
	bt = b.trace()

	parent = classifyEdge(e)
	parent.edges.append(e)
		


clsMatrix = ((-1, 0, 2), (0, -1, 1), (2, 1, -1))

def classify(n1, n2, n3, e, cache):
	acls = e.a.classify(n1, n2, n3, cache)
	bcls = e.b.classify(n1, n2, n3, cache)
	return clsMatrix[acls][bcls]


def calculateLocal():
	pass

def pivot(n, explore=1.0):
	if n.parent == None:
		return

	isLeft = n.parent.left == n
	n1, n2, n3 = n.left, n.right, (n.parent.right if isLeft else n.parent.left)

	edges = [[],[],[]]

	cache = {}

	for e in n.edges:
		cls = classify(n1, n2, n3, e, cache)
		edges[cls].append(e)

	for e in n.parent.edges:
		cls = classify(n1, n2, n3, e, cache)
		edges[cls].append(e)


	subLeft = random.random() < 0.5

	if subLeft:
		edges[1], edges[2] = edges[2], edges[1]
		n1, n2 = n2, n1

	c0 = n1.leafCount()
	c1 = n2.leafCount()
	c2 = n3.leafCount()
	e0 = len(edges[0])
	e1 = len(edges[1])
	e2 = len(edges[2])

	# Swaping n1/n2 and e1/e2 doesn't change this.
	p1 = calculatePartialH(c0, c1, e0)
	p2 = calculatePartialH(c0+c1, c2, e1+e2)
	original = -(p1+p2)

	p1 = calculatePartialH(c0, c2, e2)
	p2 = calculatePartialH(c0+c2, c1, e0+e1)
	possible = -(p1+p2)
	
	delta = possible-original

	if accept(delta, explore):
		if subLeft:
			n.left = n3
		else:
			n.right = n3

		if isLeft:
			n.parent.right = n2
		else:
			n.parent.left = n2

		n.edges = edges[2]
		n.parent.edges = edges[0]
		n.parent.edges.extend(edges[1])

		n.recount()
		n.parent.recount()



def createRandomHG(leafs):
	# Create inital data structure
	l = [Leaf(i) for i in leafs]
	n = [Node(l[0], l[1])]
	for i in xrange(2, len(leafs)):
		n.append(Node(n[i-2], l[i]))

	return n[-1], n, l

def cluster(l, n):
	iterations = len(l)*len(l)*20

	start  = time.clock()

	if len(l) > 2:
		for i in range(iterations):
			explore = 1.0-i/float(iterations)
			#explore = 1.0
			
			choice = random.choice(n)
			
			# Must be an internal node.
			while choice.parent == None: choice = random.choice(n)
			
			pivot(choice, explore)

	end = time.clock()

	print
	sec = (end-start)/iterations
	print "%f ms per iteration" % (sec*1000.0)

##	c = 5000
##	est = sec*c*c*10
##	print "%f m for %d" % (est/60.0, c)

	print
