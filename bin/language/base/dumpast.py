from util.typedispatch import *
from language.python import ast

class DumpAST(TypeDispatcher):
	def __init__(self, f):
		self.f = f

	def writeLine(self, s, tabs=0):
		self.f.write('\t'*tabs)
		self.f.write(str(s))
		self.f.write('\n')

	@dispatch(list, tuple)
	def visitlist(self, node, tabs=0):
		self.writeLine('[', tabs)
		for child in node:
			self(child, tabs)
		self.writeLine(']', tabs)

	@dispatch(ast.Assign)
	def visitAssign(self, node, tabs):
		if len(node.lcls) == 1:
			target = repr(node.lcls[0])
		else:
			target = "<%s>" % (",".join([repr(lcl) for lcl in node.lcls]))

		#self.writeLine("%s = %r" % (target, node.expr), tabs)
		self.writeLine(repr(node.expr), tabs)
		self.writeLine("=> %s" % (target), tabs+1)

	@dispatch(int, float, str, type(None))
	def visitConst(self, node, tabs):
		self.writeLine(repr(node), tabs)

	@defaultdispatch
	def default(self, node, tabs=0):
		if isinstance(node, (ast.Expression, ast.LLExpression, ast.LLStatement, ast.Assign)) or node.isControlFlow():
			self.writeLine(repr(node), tabs)
		else:
			self.writeLine(type(node).__name__, tabs)

			for name, child in node.fields():
				if child:
					self.writeLine('+%s' % name, tabs+1)
					self(child, tabs+1)
