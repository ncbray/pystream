from util.typedispatch import *
from language.python import ast
from language.python.annotations import originString

from language.glsl import ast as glsl

from . import intrinsics

from language.glsl import codegen

class TranslationError(Exception):
	def __init__(self, code, node, reason):
		self.code   = code
		self.node   = node
		self.reason = reason

		trace = '\n'.join([originString(origin) for origin in node.annotation.origin])

		Exception.__init__(self, "\n\n".join([reason, repr(code), trace, repr(node)]))

class TemporaryLimitation(TranslationError):
	pass


class GLSLTranslator(StrictTypeDispatcher):
	def __init__(self, intrinsicRewrite):
		self.intrinsicRewrite = intrinsicRewrite

		self.builtinTypeLUT = {int:glsl.BuiltinType('int'),
			float:glsl.BuiltinType('float'),
			bool:glsl.BuiltinType('bool')}

	def _getTypeFromRef(self, obj):
		return obj.xtype.obj.type.pyobj

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
		if node not in self.localLUT:
			lcl = glsl.Local(self.getType(node, node.annotation.references[0]), node.name)
			self.localLUT[node] = lcl
		else:
			lcl = self.localLUT[node]
		return lcl

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
		if len(node.exprs) != 1:
			raise TemporaryLimitation(self.code, node, "Can only translate returns with a single value.")
		return glsl.Return(self(node.exprs[0]))

	@dispatch(list)
	def visitList(self, node):
		return [self(child) for child in node]

	@dispatch(ast.Suite)
	def visitSuite(self, node):
		return glsl.Suite(self(node.blocks))

	def processCode(self, node):
		self.code = node
		self.localLUT = {}

		body = self(node.ast)
		return glsl.Code(node.name, [],glsl.BuiltinType('void'), body)

def translate(console, dataflow, interface):
	console.begin('translate to glsl')

	try:
		translator = GLSLTranslator(intrinsics.makeIntrinsicRewriter(dataflow.extractor))
		cg = codegen.GLSLCodeGen()

		for code, expr, args in interface.entryPoint:
			console.output(str(code))
			result = translator.processCode(code)
			print cg(result)
			print
	finally:
		console.end()