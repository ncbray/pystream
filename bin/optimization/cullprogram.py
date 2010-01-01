from util.typedispatch import *
from language.python import ast

from language.python.program import Object
from analysis import programculler


# Eliminates all unreferenced code from a given program
class CodeContextCuller(TypeDispatcher):
	@dispatch(ast.leafTypes)
	def visitLeaf(self, node):
		pass

	@dispatch(ast.Local)
	def visitLocal(self, node):
		if node not in self.locals:
			self.locals.add(node)
			node.annotation = node.annotation.contextSubset(self.remap)

	@defaultdispatch
	def default(self, node):
		node.visitChildren(self)
		if node.annotation is not None:
			node.annotation = node.annotation.contextSubset(self.remap)

	def process(self, code, contexts):
		self.locals = set()
		self.remap  = []
		for cindex, context in enumerate(code.annotation.contexts):
			if context in contexts:
				self.remap.append(cindex)

		code.annotation = code.annotation.contextSubset(self.remap)

		self(code.codeparameters)
		self(code.ast)


def evaluate(compiler):
	with compiler.console.scope('cull'):
		ccc = CodeContextCuller()
		liveContexts = programculler.findLiveContexts(compiler.interface)

		for code, contexts in liveContexts.iteritems():
			if len(code.annotation.contexts) != len(contexts):
				ccc.process(code, contexts)

		compiler.liveCode = set(liveContexts.iterkeys())

		# TODO cull objects
		# Object culling is complicated by implicit read/writes in function
		# call resolution, etc.
