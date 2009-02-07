from analysis.astcollector import getOps
from programIR.python import ast

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
		code, context = node

		self.liveFunc.add(code)
		self.liveFuncContext.add(node)

		if code not in self.invokes:
			self.invokes[code] = set()

		if node not in self.invokesContext:
			self.invokesContext[node] = set()

		children = []

		funcinfo = self.db.functionInfo(code)
		ops, lcls = getOps(code)
		for op in ops:
			opinfo = funcinfo.opInfo(op)
			copinfo = opinfo.context(context)

			for dstc, dstf in copinfo.invokes:
				child = (dstf, dstc)
				self.invokes[code].add(dstf)
				self.invokesContext[node].add(child)
				children.append(child)
		return children


def findLiveFunctions(db, entryPoints):
	cgf = CallGraphFinder(db)

	entry = set()
	for code, funcobj, args in entryPoints:
		assert isinstance(code, ast.Code), type(code)

		entry.add(code)

		# HACK for finding the entry context, assumes there's only one context.
		for context in db.functionInfo(code).contexts:
			cgf.process((code, context))

	live = cgf.liveFunc
	G = cgf.invokes
	head = None
	G[head] = entry

	return live, G

