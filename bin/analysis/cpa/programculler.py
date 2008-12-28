from analysis.astcollector import getOps

class Finder(object):
	def __init__(self):
		self.processed = set()
		
	def process(self, node):
		if node not in self.processed:
			self.processed.add(node)
			for child in self.children(node):
				self.process(child)

class CallGraphFinder(Finder):
	def __init__(self, db):
		Finder.__init__(self)
		self.db = db

		self.liveFunc = set()
		self.liveFuncContext = set()
		self.invokes = {}
		self.invokesContext = {}

	def children(self, node):
		func, context = node

		self.liveFunc.add(func)
		self.liveFuncContext.add(node)

		if func not in self.invokes:
			self.invokes[func] = set()

		if node not in self.invokesContext:
			self.invokesContext[node] = set()

		children = []

		funcinfo = self.db.functionInfo(func)
		ops, lcls = getOps(func)
		for op in ops:
			opinfo = funcinfo.opInfo(op)
			copinfo = opinfo.context(context)
			
			for dstc, dstf in copinfo.invokes:
				child = (dstf, dstc)
				self.invokes[func].add(dstf)
				self.invokesContext[node].add(child)
				children.append(child)
		return children


def findLiveFunctions(db, entryPoints):
	cgf = CallGraphFinder(db)

	entry = set()
	for func, funcobj, args in entryPoints:

		entry.add(func)

		# HACK for finding the entry context, assumes there's only one context.
		for context in db.functionInfo(func).contexts:
			cgf.process((func, context))

	live = cgf.liveFunc
	G = cgf.invokes
	head = None
	G[head] = entry

	return live, G
		
