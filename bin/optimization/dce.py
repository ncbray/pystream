from util.typedispatch import *
from programIR.python import ast

from dataflow.reverse import *

import util.xform

##class LiveOp(object):
##	simple = set((ast.GetGlobal, ast.BuildTuple, ast.Local, ast.Existing))
##	
##	def __call__(self, node):
##		if type(node) in self.simple:
##			for child in ast.children(node):
##				if self(child):
##					return True
##			else:
##				return False
##		else:
##			return True
##		
##
##class MarkLive(object):
##	__metaclass__ = typedispatcher
##
##	def __init__(self):
##		self.liveOp = LiveOp()
##		self.live = set()
##
##	def markLive(self, node):
##		if isinstance(node, (list, tuple)): return
##
##		if not node in self.live:
##			self.live.add(node)	
##			util.xform.visitAllChildren(self.markLive, node)
##
##	@dispatch(ast.Return, ast.Raise,
##		  ast.SetAttr, ast.SetSubscript, ast.SetSlice,
##		  ast.SetGlobal,
##		  ast.DeleteAttr, ast.DeleteSubscript, ast.DeleteSlice,
##		  ast.Print)
##	def visitMustUse(self, node):
##		self.markLive(node)
##
##
##	@dispatch(ast.Break, ast.Continue, ast.Delete)
##	def visitSimple(self, node):
##		pass
##
##	@dispatch(ast.Assign)
##	def visitAssign(self, node):
##		if node.lcl in self.live or self.liveOp(node.expr):
##			self.markLive(node.expr)
##
##	@dispatch(ast.Discard)
##	def visitDiscard(self, node):
##		if self.liveOp(node.expr):
##			self.markLive(node.expr)
##
##	@dispatch(ast.UnpackSequence)
##	def visitUnpackSequence(self, node):
##		# HACK
##		self.markLive(node.expr)
##
##	
##	@defaultdispatch
##	def default(self, node):
##		assert False, repr(node)



class MarkLocals(object):
	__metaclass__ = typedispatcher

	@dispatch(ast.Local)
	def visitLocal(self, node):
		self.flow.define(node, top)

	@defaultdispatch
	def default(self, node):
		util.xform.visitAllChildren(self, node)


class MarkLive(object):
	__metaclass__ = typedispatcher

	def __init__(self, adb, function):
		self.adb = adb
		self.function = function
		self.marker = MarkLocals()

	def hasNoSideEffects(self, node):
		return isinstance(node, (ast.GetGlobal, ast.Existing, ast.Local, ast.Load, ast.Allocate)) or not self.adb.hasSideEffects(self.function, node)
		#return not self.adb.hasSideEffects(node)
		#return False

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

	t = MutateFunction(traverse)


	oldcode = node.code	
	result = t(node)

	return result

	
