from __future__ import absolute_import

import programIR.python.ast as code
from util.visitor import StandardVisitor

from . import opnames


class SSADefinitions(object):
	def __init__(self):
		self.defn = {}

	def define(self, local, defn, merge=False):
		assert not local in self.defn, "Attempt to redefine %r" % local
		assert local != defn

		defn = constify(defn)

		# Reach for the definition
		while defn in self.defn:
			assert defn != self.defn[defn]
			defn = self.defn[defn]

		self.defn[local] = defn
		
		#print local, "->", defn
		return local

	def reachTrivial(self, expr):
		defn = self.definition(expr)
		
		if defn.isReference():
			return defn
		else:
			return expr

	def definition(self, local):
		#assert isinstance(local, code.Local), local
		return self.defn.get(local, local)
		
def constify(node):
	return node


def emitInstruction(op, instructions, merge=False):
	assert isinstance(op, code.SimpleStatement), op
	instructions.append(op)	


class UsageCounter(StandardVisitor):
	__slots__ = 'uses'
	def __init__(self):
		self.uses = {}

	def addUse(self, node):
		if not node in self.uses:
			self.uses[node] = 1
		else:
			self.uses[node] += 1

	def isUsed(self, node):
		return node in self.uses		
	
	def visitReturn(self, node):
		self.addUse(node)
		if node.expr != None:
			self.visit(node.expr)

	def visitLocal(self, node):
		self.addUse(node)

	def visitConstant(self, node):
		self.addUse(node)

	def visitGetGlobal(self, node):
		self.addUse(node)

	def visitGetCell(self, node):
		self.addUse(node)

	def visitSetCell(self, node):
		self.addUse(node)

	def visitUnaryPrefixOp(self, node):
		self.addUse(node)
		self.visit(node.expr)

	def visitNot(self, node):
		self.addUse(node)
		self.visit(node.expr)

	def visitConvertToBool(self, node):
		self.addUse(node)
		self.visit(node.expr)

	def visitBuildTuple(self, node):
		self.addUse(node)
		for arg in node.args:
			self.visit(arg)

	def visitBuildList(self, node):
		self.addUse(node)
		for arg in node.args:
			self.visit(arg)

	def visitBinaryOp(self, node):
		self.addUse(node)
		self.visit(node.left)
		self.visit(node.right)

	def visitGetSubscript(self, node):
		self.addUse(node)
		self.visit(node.expr)
		self.visit(node.subscript)


	def visitGetAttr(self, node):
		self.addUse(node)
		self.visit(node.expr)

	def visitSetAttr(self, node):
		self.addUse(node)
		self.visit(node.expr)
		self.visit(node.value)


	def visitCall(self, node):
		self.addUse(node)
		self.visit(node.expr)
		for arg in node.args:
			self.visit(arg)

	def visitCallMethod(self, node):
		self.addUse(node)
		self.visit(node.expr)
		for arg in node.args:
			self.visit(arg)

	def visitCallFunction(self, node):
		self.addUse(node)
		#self.visit(node.expr)
		for arg in node.args:
			self.visit(arg)

	def visitCallClass(self, node):
		self.addUse(node)
		#self.visit(node.expr)
		for arg in node.args:
			self.visit(arg)

	def visitMerge(self, node):
		self.addUse(node)
		for arg in node.args:
			if arg != None: self.visit(arg)


	def visitAssign(self, node):
		self.addUse(node)
		self.visit(node.expr)
		self.visit(node.lcl)


	def visitDiscard(self, node):
		self.addUse(node)
		self.visit(node.expr)

	# Assignments... a hack.
	
	def visitAssignLocal(self, node):
		return self.isUsed(node.lcl)

	def visitUnpackSequence(self, node):
		self.addUse(node)
		self.visit(node.expr)
		
		for target in node.targets:
			if self.visit(target):
				return True
		return False

class CanEliminate(StandardVisitor):
	def __init__(self, usage):
		self.usage = usage
	
	def visitUnpackSequence(self, node):
		for target in node.targets:
			if self.usage.isUsed(target):
				return False
		return True

	def visitBuildTuple(self, node):
		return True

	def visitLocal(self, node):
		return not self.usage.isUsed(self)

	def visitConstant(self, node):
		return True

	def visitGetGlobal(self, node):
		return True

	def visitMerge(self, node):
		for arg in node.args:
			if not self.visit(arg):
				return False
		return True

	def visitGetAttr(self, node):
		# HACK what about properties?
		return self.visit(node.expr) 


	def visitGetCell(self, node):
		return True

	def visitSetCell(self, node):
		return False


	def visitSetAttr(self, node):
		return False # This is conservative.		

	def visitCall(self, node):
		return False # This is conservative.

	def visitCallMethod(self, node):
		return False # This is conservative.

	def visitCallFunction(self, node):
		return False # This is conservative.

	def visitCallClass(self, node):
		return False # This is conservative.

	def visitBinaryOp(self, node):
		return False # This is conservative.

	def visitUnaryPrefixOp(self, node):
		return False # This is conservative.

	def visitAssign(self, node):
		return False

	def visitDiscard(self, node):
		return self.visit(node.expr)

class DeadCodeEliminator(StandardVisitor):
	def __init__(self):
		self.usage = UsageCounter()
		self.canEliminate = CanEliminate(self.usage)

	def collectUsage(self, node):
		self.usage.walk(node)

	def process(self, block, loop=False):
		self.handleInstructions(block.onExit, loop)
		self.visit(block)
		self.handleInstructions(block.onEntry, loop)

	def handleInstructions(self, instructions, loop=False):
		for i in reversed(range(len(instructions))):
			op = instructions[i]

			if isinstance(op, code.Assign) and not loop:
				if not self.usage.isUsed(op.lcl):
					op = code.Discard(op.expr)
					instructions[i] = op

			if self.canEliminate.walk(op):
				del instructions[i]
				# No need to modify the index, as we're doing this in reverse.
			else:	
				self.collectUsage(op)
	
	def visitSuite(self, block):
		for child in reversed(block.blocks):
			self.process(child)

	def visitCondition(self, block):
		self.collectUsage(block.conditional)
		self.process(block.preamble)

	def visitShortCircutOr(self, block):
		for term in reversed(block.terms):
			self.process(term)

	def visitShortCircutAnd(self, block):
		for term in reversed(block.terms):
			self.process(term)


	def visitSwitch(self, block):
		self.process(block.f)
		self.process(block.t)
		self.process(block.condition)


	def visitTryExceptFinally(self, block):
		if block.finally_: self.process(block.finally_)
		if block.except_: self.process(block.except_)
		self.process(block.try_)

	def visitWhile(self, block):
		self.process(block.body, True)
		self.process(block.condition, True)

	def visitFor(self, block):
		# HACK
		#self.handleInstructions(block.merges, True)

		self.process(block.body, True)
		self.collectUsage(block.iterator)

	def visitBreak(self, block):
		pass

	def visitContinue(self, block):
		pass

	def visitReturn(self, block):
		self.collectUsage(block.expr)

	def visitRaise(self, block):
		if block.exception: self.collectUsage(block.exception)
		if block.parameter: self.collectUsage(block.parameter)
		if block.traceback: self.collectUsage(block.traceback)

	def visitFunction(self, block):
		self.process(block.code)
