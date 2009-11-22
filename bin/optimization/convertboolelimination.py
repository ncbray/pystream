from util.typedispatch import *

from language.python import ast

from optimization.rewrite import rewrite

# TODO this does not propagate through assignments.
# This should be a proper dataflow analysis?
class InferBoolean(TypeDispatcher):
	def __init__(self):
		self.lut = {}
		self.converts = []
	
	@dispatch(str, type(None), ast.Return, ast.Local, ast.Store, ast.Discard)
	def visitLeaf(self, node):
		pass
	
	@dispatch(ast.Suite, ast.Switch, ast.Condition)
	def visitOK(self, node):
		node.visitChildren(self)

	@dispatch(ast.Assign)
	def visitAssign(self, node):
		if isinstance(node.expr, ast.ConvertToBool):
			self.converts.append(node.expr)
			
		if node.expr.alwaysReturnsBoolean() and len(node.lcls) == 1:
			self.define(node.lcls[0])
	
	@dispatch(ast.CodeParameters)
	def visitCodeParameters(self, node):
		self.undef(node.selfparam)
		for p in node.params:
			self.undef(p)
		self.undef(node.vparam)
		self.undef(node.kparam)
	
	def process(self, code):
		code.visitChildrenForced(self)
	
	def define(self, lcl):
		if not lcl in self.lut:
			self.lut[lcl] = True
	
	def undef(self, lcl):
		self.lut[lcl] = False
	
	def isBoolean(self, expr):
		if expr.alwaysReturnsBoolean():
			return True
		
		return self.lut.get(expr, False)

# This transformation is slightly unsound, as conversions of
# possibly undefined locals will be eliminated
def evaluateCode(compiler, code):
	infer = InferBoolean()
	infer.process(code)
	
	if infer.converts:
		# Eliminate ConvertToBool nodes that take booleans as arguments
		replace = {}
		for convert in infer.converts:
			if infer.isBoolean(convert.expr):
				replace[convert] = convert.expr

		if replace:
			rewrite(compiler, code, replace)