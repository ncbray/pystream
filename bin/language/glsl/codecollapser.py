from util.typedispatch import *
from . import ast as glsl

class CollapserAnalysis(TypeDispatcher):
	def __init__(self):
		self.stats   = {}
		self.inputs  = set()
		self.outputs = set()
		
	def addUse(self, lcl):
		uses, defns = self.stats.get(lcl, (0, 0))		
		self.stats[lcl] = (uses+1, defns)

	def addDefn(self, lcl):
		uses, defns = self.stats.get(lcl, (0, 0))		
		self.stats[lcl] = (uses, defns+1)
		
	@dispatch(str, glsl.BuiltinType, glsl.Constant)
	def visitLeaf(self, node):
		pass	

	@dispatch(glsl.Input)
	def visitInput(self, node):
		self.addUse(node.decl)
		self.inputs.add(node.decl.name)

	@dispatch(glsl.Uniform)
	def visitUniform(self, node):
		self.addUse(node.decl)

	@dispatch(glsl.Local)
	def visitLocal(self, node):
		self.addUse(node)
	
	@dispatch(glsl.Assign)
	def visitAssign(self, node):
		self(node.expr)
		
		if isinstance(node.lcl, glsl.Local):
			self.addDefn(node.lcl)
		elif isinstance(node.lcl, glsl.Output):
			self.addDefn(node.lcl.decl)
			self.outputs.add(node.lcl.decl.name)
		else:
			assert False, type(node.lcl)
	
	@dispatch(glsl.Suite,
			glsl.Discard, glsl.Return,
			glsl.BinaryOp, glsl.UnaryPrefixOp, glsl.Constructor,
			glsl.Load,
			glsl.IntrinsicOp # HACK can intrinsic ops mutate?
			)
	def visitOK(self, node):
		node.visitChildren(self)	
	
	def process(self, code):
		code.visitChildrenForced(self)
		return self.digest()
		
	def digest(self):
		# TODO take into account stores / flow control?
		
		inout = self.inputs.intersection(self.outputs)
		
		possible = set()
		
		for node, (uses, defns) in self.stats.iteritems():
			if isinstance(node, glsl.Local):
				if defns == 1 and uses == 1:
					possible.add(node)
			elif isinstance(node, glsl.UniformDecl):
				if uses == 1:
					possible.add(node)
			elif isinstance(node, glsl.InputDecl):
				if node.name in inout: continue
				possible.add(node)
			elif isinstance(node, glsl.OutputDecl):
				pass
			else:
				assert False, node
		
		return possible
		
class CollapserTransform(TypeDispatcher):
	def __init__(self, possible):
		self.possible = possible
		self.lut = {}

	@dispatch(str, glsl.BuiltinType, glsl.Constant)
	def visitLeaf(self, node):
		return node	

	@dispatch(glsl.Input)
	def visitInput(self, node):
		return node

	@dispatch(glsl.Uniform)
	def visitUniform(self, node):
		return node

	@dispatch(glsl.Local)
	def visitLocal(self, node):
		return self.lut.get(node, node)
	
	@dispatch(glsl.Assign)
	def visitAssign(self, node):
		
		expr = self(node.expr)
				
		if isinstance(node.lcl, glsl.Local):
			canCollapse = True
			
			# Don't collapse inouts
			if isinstance(expr, glsl.Input) and expr.decl not in self.possible:
				canCollapse = False
			
			canCollapse &= node.lcl in self.possible
			if canCollapse:
				self.lut[node.lcl] = expr
				return []
		elif isinstance(node.lcl, glsl.Output):
			pass
		else:
			assert False, type(node.lcl)

		return glsl.Assign(expr, node.lcl)

	
	@dispatch(glsl.Suite,
			glsl.Discard, glsl.Return,
			glsl.BinaryOp, glsl.UnaryPrefixOp, glsl.Constructor,
			glsl.Load,
			glsl.IntrinsicOp # HACK can intrinsic ops mutate?
			)
	def visitOK(self, node):
		return node.rewriteChildren(self)	
	
	def process(self, code):
		return glsl.Code(code.name, code.params, code.returnType, self(code.body))
	
def evaluateCode(compiler, code):
	ca = CollapserAnalysis()
	possible = ca.process(code)
	ct = CollapserTransform(possible)
	code = ct.process(code)
	return code
