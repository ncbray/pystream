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

	def codeName(self):
		return "shader_program"

	def codeParameters(self):
		return util.calling.CalleeParams(self.selfparam, self.parameters, self.parameternames, [], self.vparam, self.kparam, self.returnparams)
