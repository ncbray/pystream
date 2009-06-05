from . base import AbstractCode

from language.python import ast
import language.base.annotation as annotation
import util.calling

# HACK
from language.python.annotations import CodeAnnotation

# Note that the annotation defaults to descriptive=True
emptyShaderProgramAnnotation = CodeAnnotation(None, True, False, None, None, None, None, None)

class ShaderProgram(AbstractCode):
	def __init__(self):
		self.selfparam = None
		self.parameters = (ast.Local('vs'), ast.Local('fs'), ast.Local('shader'))
		self.parameternames = ('vs', 'fs', 'shader')
		self.vparam = ast.Local('streams')
		self.kparam = None
		self.returnparams = [ast.Local('return_shader_program')]

		self.annotation = emptyShaderProgramAnnotation

		self.vsCall = ast.Call(self.parameters[0], (self.parameters[2],), [], self.vparam, None)
		self.fsCall = ast.Call(self.parameters[1], (self.parameters[2],), [], self.vparam, None)

	def codeName(self):
		return "shader_program"

	def codeParameters(self):
		return util.calling.CalleeParams(self.selfparam, self.parameters, self.parameternames, [], self.vparam, self.kparam, self.returnparams)

	# HACK pulled from AST node?
	def rewriteAnnotation(self, **kwds):
		self.annotation = self.annotation.rewrite(**kwds)


	def collectNodes(self, collector):
		collector(self.selfparam)
		collector(self.parameters)
		collector(self.vparam)
		collector(self.kparam)
		collector(self.returnparams)

		collector(self.vsCall)
		collector(self.fsCall)