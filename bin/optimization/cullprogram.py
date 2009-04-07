from util.typedispatch import *
from language.python import ast

from language.python.program import Object
from decompiler.constantfinder import findCodeReferencedObjects
from analysis import programculler


# Eliminates all unreferenced code from a given program
class CodeContextCuller(object):
	__metaclass__ = typedispatcher

	@dispatch(ast.Code, type(None), int, float, str)
	def visitLeaf(self, node):
		pass

	@dispatch(ast.Local)
	def visitLocal(self, node):
		if node not in self.locals:
			self.locals.add(node)
			node.annotation = node.annotation.contextSubset(self.remap)

	@dispatch(list, tuple)
	def visitNoAnnotation(self, node):
		visitAllChildren(self, node)


	@defaultdispatch
	def default(self, node):
		visitAllChildren(self, node)
		if node.annotation is not None:
			node.annotation = node.annotation.contextSubset(self.remap)

	def process(self, code, contexts):
		self.locals = set()
		self.remap  = []
		for cindex, context in enumerate(code.annotation.contexts):
			if context in contexts:
				self.remap.append(cindex)

		code.annotation = code.annotation.contextSubset(self.remap)

		self(code.selfparam)
		self(code.parameters)
		self(code.parameternames)
		self(code.vparam)
		self(code.kparam)
		self(code.returnparam)
		self(code.ast)


def cullProgram(entryPoints, db):
	ccc = CodeContextCuller()
	liveContexts = programculler.findLiveContexts(entryPoints)

	for code, contexts in liveContexts.iteritems():
		if len(code.annotation.contexts) != len(contexts):
			ccc.process(code, contexts)

	db.liveCode = set(liveContexts.iterkeys())

	# TODO cull objects
	# Object culling is complicated by implicit read/writes in function
	# call resolution, etc.