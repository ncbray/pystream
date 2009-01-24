from util.typedispatch import *
from programIR.python import ast

from dataflow.reverse import *

import util.xform

class MarkLocals(object):
	__metaclass__ = typedispatcher

	@dispatch(ast.Local)
	def visitLocal(self, node):
		self.flow.define(node, top)

	@defaultdispatch
	def default(self, node):
		util.xform.visitAllChildren(self, node)


nodesWithNoSideEffects = (ast.GetGlobal, ast.Existing, ast.Local, ast.Load, ast.Allocate)

class MarkLive(object):
	__metaclass__ = typedispatcher

	def __init__(self, adb, function):
		self.adb = adb
		self.function = function
		self.marker = MarkLocals()

	def hasNoSideEffects(self, node):
		return isinstance(node, nodesWithNoSideEffects) or not self.adb.hasSideEffects(self.function, node)

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
		if self.flow.lookup(node.lcl) is not undefined:
			self.flow.undefine(node.lcl)
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




def dce(extractor, adb, node):
	rewrite = MarkLive(adb, node)
	traverse = ReverseFlowTraverse(rewrite)

	# HACK
	rewrite.flow = traverse.flow
	rewrite.marker.flow = traverse.flow

	t = MutateCode(traverse)

	result = t(node)

	return result


