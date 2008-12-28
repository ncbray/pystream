from __future__ import absolute_import
from util.visitor import StandardVisitor

from programIR.python import program

class LLCodeExtractor(StandardVisitor):
	def __init__(self, builder):
		self.builder = builder
		self.created = set()

	def makeBytecode(self, node):
		self.builder.makeBytecode(self.function, node, False)
		
	def visitLocal(self, node):
		if not node in self.created:
			self.builder.makeVariable(self.function, node)
			self.created.add(node)
			
		return node


	def visitlist(self, node):
		return [self.visit(arg) for arg in node]

	def visittuple(self, node):
		return tuple([self.visit(arg) for arg in node])

	def visitExisting(self, node):
		assert isinstance(node.object, program.AbstractObject), node # HACK?
		return node.object

	def visitAllocate(self, node):
		self.makeBytecode(node)
		expr = self.visit(node.expr)
		self.builder.addTuple('allocateOp', node, expr)		
		return node

	def visitLoad(self, node):
		self.makeBytecode(node)
		expr = self.visit(node.expr)
		name = self.visit(node.name)
		self.builder.addTuple('load', node, expr, node.fieldtype, name)
		return node

	def visitStore(self, node):
		self.makeBytecode(node)
		expr = self.visit(node.expr)
		name = self.visit(node.name)
		value = self.visit(node.value)
		self.builder.addTuple('store', node, expr, node.fieldtype, name, value)
		return node

	def makeOperation(self, b, enum, expr, args):
		assert enum == 'Call'

		#self.builder.addTuple('operation', b, enum, expr)		
		self.builder.addTuple('call', b, expr)

		for i, arg in enumerate(args):
			self.builder.addTuple('actualParam', b, i, arg)		


	def visitAssign(self, node):
		target = self.visit(node.target)
		expr = self.visit(node.expr)


		if node.expr.isReference():
			self.builder.addTuple('merge', target, expr)
		else:
			self.builder.addTuple('opResult', target, 0, expr)


	def visitDiscard(self, node):
		expr = self.visit(node.expr)

	def visitReturn(self, node):
		if not isinstance(node.expr, (list, tuple)):
			expr = (node.expr,)
			
		for i, e in enumerate(node.expr):
			e = self.visit(e)
			self.builder.addTuple('returns', self.function, i, e)

	def visitOperation(self, node):
		self.makeBytecode(node)
		
		expr = self.visit(node.expr)
		args = self.visit(node.args)

		self.makeOperation(node, node.opType, expr, args)

		return node

	def visitInstructionBlock(self, node):
		for inst in node.instructions:
			self.visit(inst)
	
	def visitFunction(self, node):
		self.function = node

		if node.selfv:
			assert hasattr(node, 'selfv'), type(node)
			selfv = self.visit(node.selfv)
			self.builder.addTuple('selfParam', node, selfv)


		args = [self.visit(arg) for arg in node.args]

		for i in range(len(args)):
			self.builder.addTuple('formalParam', node, i, args[i])


		self.visit(node.body)

		
		return node
