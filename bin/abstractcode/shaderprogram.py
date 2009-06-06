from . base import AbstractCode

from language.python.ast import *
import language.base.annotation as annotation
import util.calling

# HACK
from language.python.annotations import CodeAnnotation

# Note that the annotation defaults to descriptive=True
emptyShaderProgramAnnotation = CodeAnnotation(None, True, False, None, None, None, None, None)

def createShaderProgram(extractor):
	name = "shader_program"

	selfparam = None
	parameters = (Local('vs'), Local('fs'), Local('shader'))
	parameternames = ('vs', 'fs', 'shader')
	vparam = Local('streams')
	kparam = None
	returnparams = [Local('return_shader_program')]

	codeparameters = CodeParameters(selfparam, parameters, parameternames, vparam, kparam, returnparams)

	vsCall     = Assign(Call(parameters[0], (parameters[2],), [],vparam, kparam), [Local('vs_return')])
	fsCall     = Assign(Call(parameters[1], (parameters[2],), [], vparam, kparam), [Local('fs_return')])
	returnExpr = Return([Existing(extractor.getObject(None))])


	sp = ShaderProgram(name, codeparameters, vsCall, fsCall, returnExpr)
	return sp

class ShaderProgram(AbstractCode):
	__fields__ = """name:str codeparameters:CodeParameters vsCall:Statement fsCall:Statement returnExpr:Return"""

	__shared__ = True

	emptyAnnotation = emptyShaderProgramAnnotation

	def codeName(self):
		return self.name

	def setCodeName(self, name):
		self.name = name

	def codeParameters(self):
		return self.codeparameters.codeParameters()

	def extractConstraints(self, ce):
		ce(self.vsCall)
		ce(self.fsCall)
		ce(self.returnExpr)