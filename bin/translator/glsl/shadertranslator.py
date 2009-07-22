from asttools.transform import *
from language.python import ast
from asttools.origin import originString

from language.glsl import ast as glsl

from . import intrinsics
from . import iotransform

class TranslationError(Exception):
	def __init__(self, code, node, reason):
		self.code   = code
		self.node   = node
		self.reason = reason

		trace = '\n'.join([originString(origin) for origin in node.annotation.origin])

		Exception.__init__(self, "\n\n".join([reason, repr(code), trace, repr(node)]))

class TemporaryLimitation(TranslationError):
	pass


class GLSLTranslator(TypeDispatcher):
	def __init__(self, intrinsicRewrite):
		self.intrinsicRewrite = intrinsicRewrite

		self.builtinTypeLUT = {int:glsl.BuiltinType('int'),
			float:glsl.BuiltinType('float'),
			bool:glsl.BuiltinType('bool')}

	def _getTypeFromRef(self, obj):
		wobj = obj.xtype.obj
		return wobj.pythonType()

	def getType(self, node, references):
		types = set([self._getTypeFromRef(ref) for ref in references])

		if len(types) != 1:
			print node, references
			raise TemporaryLimitation(self.code, node, "Cannot handle multiple references.")

		type = types.pop()
		# TODO validate

		return glsl.BuiltinType(type.__name__)

	@dispatch(ast.Local)
	def visitLocal(self, node):
		if node not in self.referenceLUT:
			path = self.shader.localToPath.get(node)
			freq = path.frequency if path is not None else None
			if freq == 'uniform':
				decl = glsl.UniformDecl(self.getType(node, node.annotation.references[0]), node.name, None)
				ref  = glsl.Uniform(decl)
			elif freq == 'input':
				# TODO input modifiers?
				decl = glsl.InputDecl(None, False, self.getType(node, node.annotation.references[0]), node.name)
				ref  = glsl.Input(decl)
			elif freq == 'output':
				# TODO input modifiers?
				decl = glsl.OutputDecl(None, False, False, self.getType(node, node.annotation.references[0]), node.name)
				ref  = glsl.Output(decl)
			else:
				ref = glsl.Local(self.getType(node, node.annotation.references[0]), node.name)

			self.referenceLUT[node] = ref
		else:
			ref = self.referenceLUT[node]
		return ref

	@dispatch(ast.Existing)
	def visitExisting(self, node):
		obj = node.object.pyobj
		if not isinstance(obj, (int, float, bool)):
			raise TranslationError(self.code, node, "Cannot have an existing reference to a non-intrinsic type.")
		return glsl.Constant(self.builtinTypeLUT[type(obj)], obj)

	@dispatch(ast.Load)
	def visitLoad(self, node):
		if node.fieldtype != 'Attribute' or not isinstance(node.name, ast.Existing) or node.name.object.pyobj not in intrinsics.fields:
			raise TranslationError(self.code, node, "Cannot only handle loads on non-intrinsic types.")

		field = intrinsics.fields[node.name.object.pyobj]

		return glsl.Load(self(node.expr), field)

	@dispatch(ast.DirectCall)
	def visitDirectCall(self, node):
		translated = self.intrinsicRewrite(self, node)

		if translated is None:
			raise TemporaryLimitation(self.code, node, "Cannot handle non-intrinsic function calls.")

		return translated

	@dispatch(ast.Call)
	def visitCall(self, node):
		raise TranslationError(self.code, node, "Cannot handle indirect calls.")


	@dispatch(ast.Assign)
	def visitAssign(self, node):
		if len(node.lcls) != 1:
			raise TemporaryLimitation(self.code, node, "Can only translate assignments with a single target.")

		return glsl.Assign(self(node.expr), self(node.lcls[0]))

	@dispatch(ast.Discard)
	def visitDiscard(self, node):
		return glsl.Discard(self(node.expr))

	@dispatch(ast.Return)
	def visitReturn(self, node):
		if len(node.exprs) > 1:
			raise TemporaryLimitation(self.code, node, "Cannot translate a return with multiple values.")

		if len(node.exprs) == 0:
			return glsl.Return(None)
		else:
			return glsl.Return(self(node.exprs[0]))

	@dispatch(list)
	def visitList(self, node):
		return [self(child) for child in node]

	@dispatch(ast.Suite)
	def visitSuite(self, node):
		return glsl.Suite(self(node.blocks))

	def processShader(self, node):
		self.code = node
		self.referenceLUT = {}

		body = self(self.code.ast)
		return glsl.Code('main', [], glsl.BuiltinType('void'), body)

	def processShaderProgram(self, node):
		self.shader = node
		vs = self.processShader(node.vs)
		fs = self.processShader(node.fs)
		return vs, fs