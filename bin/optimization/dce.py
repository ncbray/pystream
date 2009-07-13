from asttools.transform import *
from language.python import ast

from dataflow.reverse import *

from analysis import tools

def liveMeet(values):
	if values:
		return top
	else:
		return undefined

# Mark a locals in an AST subtree as used.
class MarkLocals(TypeDispatcher):
	@dispatch(ast.Local)
	def visitLocal(self, node):
		self.flow.define(node, top)

	@defaultdispatch
	def default(self, node):
		visitAllChildren(self, node)


nodesWithNoSideEffects = (ast.GetGlobal, ast.Existing, ast.Local, ast.Load, ast.Allocate, ast.BuildTuple, ast.BuildList, ast.BuildMap)

class MarkLive(TypeDispatcher):
	def __init__(self, function):
		self.function = function
		self.marker = MarkLocals()

	def hasNoSideEffects(self, node):
		return isinstance(node, nodesWithNoSideEffects) or not tools.mightHaveSideEffect(node)

	@dispatch(ast.Condition)
	def visitCondition(self, node):
		self.marker(node.conditional)
		return node

	@dispatch(ast.Discard)
	def visitDiscard(self, node):
		if self.hasNoSideEffects(node.expr):
			return []
		else:
			self.marker(node)
			return node

	@dispatch(ast.Assign)
	def visitAssign(self, node):
		used = any([self.flow.lookup(lcl) is not undefined for lcl in node.lcls])
		if used:
			for lcl in node.lcls:
				self.flow.undefine(lcl)
			self.marker(node.expr)
			return node

		elif self.hasNoSideEffects(node.expr):
			return []
		else:
			node = ast.Discard(node.expr)
			node = self(node)
			return node

	@dispatch(ast.Delete)
	def visitDelete(self, node):
		self.flow.undefine(node.lcl)

	@defaultdispatch
	def default(self, node):
		if isinstance(node, ast.SimpleStatement):
			self.marker(node)
		return node

	@dispatch(ast.Return)
	def visitReturn(self, node):
		for lcl in self.initialLive:
			self.flow.define(lcl, top)
		self.marker(node)
		return node


def evaluateCode(compiler, node, initialLive=None):
	rewrite = MarkLive(node)
	traverse = ReverseFlowTraverse(liveMeet, rewrite)

	# HACK
	rewrite.flow = traverse.flow
	rewrite.marker.flow = traverse.flow

	t = MutateCode(traverse)

	# For shader translation, locals may be used as outputs.
	# We need to retain these locals.
	rewrite.initialLive = initialLive if initialLive != None else ()

	result = t(node)

	return result


