from util.visitor import StandardVisitor

# HACK
from .. python.ast import Expression, Assign

class DumpAST(StandardVisitor):
	def __init__(self, f):
		super(DumpAST, self).__init__()
		self.f = f

	def writeLine(self, s, tabs=0):
		self.f.write('\t'*tabs)
		self.f.write(str(s))
		self.f.write('\n')

	def dumpList(self, node, tabs):
		self.writeLine('[', tabs)
		for child in node:
			self.visit(child, tabs)
		self.writeLine(']', tabs)


	def visitlist(self, node, tabs=0):
		self.dumpList(node, tabs)

	def visittuple(self, node, tabs=0):
		self.dumpList(node, tabs)


	def visitAssign(self, node, tabs):
		self.writeLine("%r = %r" % (node.lcl, node.expr), tabs)
		
	def default(self, node, tabs=0):
		if isinstance(node, (int, float, str)) or node==None:
			self.writeLine(node, tabs)
		elif isinstance(node, (Expression, Assign)) or node.isControlFlow():
			self.writeLine(repr(node), tabs)
		else:
			self.writeLine(type(node).__name__, tabs)

			for name, child in node.fields():
				if child:
					self.writeLine('+%s' % name, tabs+1)
					self.visit(child, tabs+1)
