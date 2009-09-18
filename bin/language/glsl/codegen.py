from asttools.transform import *
from . import ast

class TypeNameGen(TypeDispatcher):
	@dispatch(ast.BuiltinType)
	def visitBuiltinType(self, node):
		return node.name

	@dispatch(ast.StructureType)
	def visitStructureType(self, node):
		return node.name

	@dispatch(ast.ArrayType)
	def visitArrayType(self, node):
		return "%s[%d]" % (self(node.type), node.count)


class FindLocals(TypeDispatcher):
	@defaultdispatch
	def visitOK(self, node):
		visitAllChildren(self, node)

	@dispatch(ast.Local)
	def visitLocal(self, node):
		self.locals.add(node)

	@dispatch(ast.Uniform)
	def visitUniform(self, node):
		self.uniforms.add(node.decl)

	@dispatch(ast.Input)
	def visitInput(self, node):
		self.inputs.add(node.decl)

	@dispatch(ast.Output)
	def visitOutput(self, node):
		self.outputs.add(node.decl)


	def processCode(self, node):
		self.locals = set()
		self(node.params)
		parameters = self.locals

		self.locals   = set()
		self.uniforms = set()
		self.inputs   = set()
		self.outputs  = set()

		self(node.body)
		return self.locals-parameters

class GLSLCodeGen(TypeDispatcher):
	precedenceLUT = {'*':4, '/':4, '%':4, '+':5, '-':5, '<<':6, '>>':6,
		'<':7, '>':7, '>=':7, '<=':7, '==':8, '!=':8,
		'&':9, '^':10, '|':11, '&&':12, '^^':13, '||':14}

	def __init__(self):
		# Changes depending on the shader and the language target.
		self.inLabel  = 'in'
		self.outLabel = 'out'

		self.typename = TypeNameGen()

		self.indent = ''

		self.localNameLUT = {}
		self.localNames   = set()
		self.uid = 0

	def wrap(self, s, prec, container):
		if prec > container:
			return "(%s)" % s
		else:
			return s

	@dispatch(ast.VariableDecl)
	def visitVariableDecl(self, node):
		initialize = '' if node.initializer is None else (" = " +self(node.initializer))
		return "%s %s%s" % (self.typename(node.type), node.name, initialize)

	@dispatch(ast.UniformDecl)
	def visitUniformDecl(self, node):
		initialize = '' if node.initializer is None else (" = " +self(node.initializer))
		return "uniform %s %s%s" % (self.typename(node.type), node.name, initialize)

	@dispatch(ast.StructureType)
	def visitStructureType(self, node):
		oldIndent = self.indent
		self.indent += '\t'
		statements = ["%s%s;\n" % (self.indent, self(field)) for field in node.fieldDecl]
		self.indent = oldIndent
		body = "".join(statements)
		return "{indent}struct {name}\n{indent}{{\n{body}{indent}}};\n".format(indent=self.indent, name=node.name, body=body)

	@dispatch(ast.BuiltinType)
	def visitBuiltinType(self, node):
		return "{indent}{name};\n".format(indent=self.indent, name=node.name)

	@dispatch(ast.Constant)
	def visitConstant(self, node, prec=17):
		if isinstance(node, str):
			return repr(node)
		else:
			return str(node.object)

	@dispatch(ast.Constructor)
	def visitConstructor(self, node, prec=17):
		typename = self.typename(node.type)
		assert isinstance(typename, str), node
		return self.wrap("%s(%s)" % (typename, ", ".join([self(arg) for arg in node.args])), 2, prec)

	@dispatch(ast.IntrinsicOp)
	def visitIntrinsicOp(self, node, prec=17):
		return self.wrap("%s(%s)" % (node.name, ", ".join([self(arg) for arg in node.args])), 2, prec)

	@dispatch(ast.Load)
	def visitLoad(self, node, prec=17):
		return self.wrap("%s.%s" % (self(node.expr, 1), node.name), 2, prec)


	@dispatch(ast.GetSubscript)
	def visitGetSubscript(self, node, prec=17):
		return self.wrap("%s[%s]" % (self(node.expr, 1), self(node.subscript, 2)), 2, prec)

	@dispatch(ast.SetSubscript)
	def visitSetSubscript(self, node, prec=17):
		return self.wrap("%s[%s] = %s" % (self(node.expr, 15), self(node.subscript, 16), self(node.value, 16)), 16, prec)


	@dispatch(ast.BinaryOp)
	def visitBinaryOp(self, node, prec=17):
		opPrec = self.precedenceLUT[node.op]
		return self.wrap("%s%s%s" % (self(node.left, opPrec), node.op, self(node.right, opPrec-1)), opPrec, prec)

	@dispatch(ast.Assign)
	def visitAssign(self, node, prec=17):
		return self.wrap("%s = %s" % (self(node.lcl, 15), self(node.expr, 16)), 16, prec)

	@dispatch(ast.Discard)
	def visitDiscard(self, node, prec=17):
		return self.wrap(self(node.expr, 16), 16, prec)

	def newLocalName(self, base):
		name = '%s_%d' % (base, self.uid)
		self.uid += 1
		return name

	def uniqueName(self, basename):
		name     = basename

		if name is None:
			basename = ''
			name = self.newLocalName(basename)

		while name in self.localNames:
			name = self.newLocalName(basename)

		self.localNames.add(name)

		return name

	@dispatch(ast.Local)
	def visitLocal(self, node, prec=17):
		if node not in self.localNameLUT:
			name = self.uniqueName(node.name)
			self.localNameLUT[node] = name
		else:
			name = self.localNameLUT[node]
		return name


	@dispatch(ast.Uniform)
	def visitUniform(self, node, prec=17):
		return self.visitLocal(node.decl)

	@dispatch(ast.Input)
	def visitInput(self, node, prec=17):
		return self.visitLocal(node.decl)

	@dispatch(ast.Output)
	def visitOutput(self, node, prec=17):
		return self.visitLocal(node.decl)

	@dispatch(ast.Return)
	def visitReturn(self, node):
		if node.expr is None:
			return "return"
		else:
			return "return %s" % self(node.expr)

	@dispatch(ast.Suite)
	def visitSuite(self, node):
		oldIndent = self.indent
		self.indent += '\t'
		statements = ["%s%s;\n" % (self.indent, self(stmt)) for stmt in node.statements]
		self.indent = oldIndent
		return "".join(statements)

	@dispatch(ast.Parameter)
	def visitParameter(self, node):
		prefix = ''
		if node.paramIn:
			prefix += 'in'
		if node.paramOut:
			prefix += 'out'

		return '%s %s %s' % (prefix, self.typename(node.lcl.type), node.lcl.name)

	@dispatch(ast.InputDecl)
	def visitInputDecl(self, node):
		return "in %s %s" % (self.typename(node.type), self.visitLocal(node))

	@dispatch(ast.OutputDecl)
	def visitOutputDecl(self, node):
		return "out %s %s" % (self.typename(node.type), self.visitLocal(node))

	@dispatch(ast.UniformDecl)
	def visitUniformDecl(self, node):
		return "uniform %s %s" % (self.typename(node.type), self.visitLocal(node))


	def makeLocalDecl(self, lcls):
		decl = "".join(["\t%s %s;\n" % (self.typename(lcl.type), self(lcl)) for lcl in lcls])
		return decl

	def makeDecl(self, lcls):
		decl = "".join(["%s;\n" % (self(lcl)) for lcl in lcls])
		return decl

	@dispatch(ast.Code)
	def visitCode(self, node):
		finder = FindLocals()
		finder.processCode(node)

		version = "#version 130"

		uniformdecl = self.makeDecl(finder.uniforms)
		inputdecl   = self.makeDecl(finder.inputs)
		outputdecl  = self.makeDecl(finder.outputs)

		header = "%s\n%s\n%s\n" % (uniformdecl, inputdecl, outputdecl)

		localdecl = self.makeLocalDecl(finder.locals)

		return "%s\n\n%s\n%s %s(%s)\n{\n%s\n%s}\n" % (version, header, self.typename(node.returnType), node.name, ", ".join([self(param) for param in node.params]), localdecl, self(node.body))