from util.typedispatch import *
from language.python import ast
from analysis.astcollector import getOps

class Finder(object):
	def __init__(self):
		self.processed = set()

	def process(self, node):
		if node not in self.processed:
			self.processed.add(node)
			for child in self.children(node):
				self.process(child)

	def children(self, node):
		raise NotImplementedError

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

		ops, _lcls = getOps(code)
		for op in ops:
			assert hasattr(op.annotation, 'invokes'), op
			invokes = op.annotation.invokes
			if invokes is not None:
				cinvokes = invokes[1][cindex]
				for dstf, dstc in cinvokes:
					child = (dstf, dstc)
					self.invokes[code].add(dstf)
					self.invokesContext[node].add(child)
					children.append(child)
		return children


def makeCGF(interface):
	cgf = CallGraphFinder()
	for code, context in interface.entryCodeContexts():
		assert context in code.annotation.contexts
		cgf.process((code, context))

	return cgf

def findLiveCode(prgm):
	cgf = makeCGF(prgm.interface)

	entry = set()
	for code in prgm.interface.entryCode():
		entry.add(code)

	G = cgf.invokes
	head = None
	G[head] = entry

	prgm.liveCode = cgf.liveFunc

	return cgf.liveFunc, G

def findLiveContexts(prgm):
	cgf = makeCGF(prgm.interface)
	prgm.liveCode = cgf.liveFunc
	return cgf.liveFuncContext


class LiveHeapFinder(TypeDispatcher):
	def __init__(self):
		TypeDispatcher.__init__(self)
		self.live = set()

	def addReferences(self, refs):
		self.live.update(refs)

	@dispatch(ast.leafTypes)
	def visitLeaf(self, node):
		pass

	@dispatch(ast.Existing)
	def visitExisting(self, node):
		self.addReferences(node.annotation.references.merged)

	@dispatch(ast.Local)
	def visitReference(self, node):
		self.addReferences(node.annotation.references.merged)

	@defaultdispatch
	def visitDefault(self, node):
		node.visitChildren(self)

	def process(self, code):
		code.visitChildrenForced(self)

# HACK this may not be 100% sound, as it only considers references
# directly embedded in the code.
def findLiveHeap(prgm):
	finder = LiveHeapFinder()
	for code in prgm.liveCode:
		finder.process(code)

	index = {}
	for obj in finder.live:
		group = obj.xtype.group()
		if not group in index:
			index[group] = []
		index[group].append(obj)

	return finder.live, index
