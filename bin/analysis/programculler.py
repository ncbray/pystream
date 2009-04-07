from analysis.astcollector import getOps
from language.python import ast

class Finder(object):
	def __init__(self):
		self.processed = set()

	def process(self, node):
		if node not in self.processed:
			self.processed.add(node)
			for child in self.children(node):
				self.process(child)

class CallGraphFinder(Finder):
	def __init__(self):
		Finder.__init__(self)
		self.liveFunc = set()
		self.liveFuncContext = {}
		self.invokes = {}
		self.invokesContext = {}

	def children(self, node):
		code, context = node

		self.liveFunc.add(code)

		if code not in self.liveFuncContext:
			self.liveFuncContext[code] = set()
		self.liveFuncContext[code].add(context)

		if code not in self.invokes:
			self.invokes[code] = set()

		if node not in self.invokesContext:
			self.invokesContext[node] = set()

		cindex = code.annotation.contexts.index(context)

		children = []

		ops, lcls = getOps(code)
		for op in ops:
			assert hasattr(op.annotation, 'invokes'), op
			invokes = op.annotation.invokes
			if invokes is not None:
				for dstf, dstc in invokes[1][cindex]:
					child = (dstf, dstc)
					self.invokes[code].add(dstf)
					self.invokesContext[node].add(child)
					children.append(child)
		return children

def makeCGF(entryPoints):
	cgf = CallGraphFinder()

	for code, funcobj, args in entryPoints:
		assert isinstance(code, ast.Code), type(code)

		# HACK for finding the entry context, assumes there's only one context.
		assert code.annotation.contexts is not None
		for context in code.annotation.contexts:
			cgf.process((code, context))
	return cgf

def findLiveFunctions(entryPoints):
	cgf = makeCGF(entryPoints)

	entry = set()
	for code, funcobj, args in entryPoints:
		entry.add(code)

	live = cgf.liveFunc
	G = cgf.invokes
	head = None
	G[head] = entry

	return live, G

def findLiveContexts(entryPoints):
	cgf = makeCGF(entryPoints)
	return cgf.liveFuncContext