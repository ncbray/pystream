from . base import AbstractCode

from language.python.ast import *
import language.base.annotation as annotation
import util.calling

# HACK
from language.python.annotations import CodeAnnotation

# Note that the annotation defaults to descriptive=True
emptyShaderProgramAnnotation = CodeAnnotation(None, True, False, None, None, None, None, None, None, None, None)

def createShaderProgram(extractor):
	name = "shader_program"

	selfparam = None
	parameters = (Local('vs'), Local('fs'), Local('shader'))
	parameternames = ('vs', 'fs', 'shader')
	streams = Local('streams')
	returnparams = [Local('return_shader_program')]

	codeparameters = CodeParameters(selfparam, parameters, parameternames, streams, None, returnparams)

	vsout = Local('vs_return')
	fsout = Local('fs_return')

	vsCall     = Assign(Call(parameters[0], (parameters[2],), [], streams, None), [vsout])
	fsCall     = Assign(Call(parameters[1], (parameters[2],), [], vsout, None), [fsout])

	junk = []
	junk.append(Return([Existing(extractor.getObject(None))]))
	junk.append(Discard(GetAttr(fsout, Existing(extractor.getObject('colors')))))

	sp = ShaderProgram(name, codeparameters, vsCall, fsCall, junk)
	return sp

class ShaderProgram(AbstractCode):
	__fields__ = """name:str codeparameters:CodeParameters vsCall:Statement fsCall:Statement junk:Statement*"""

	__shared__ = True

	__emptyAnnotation__ = emptyShaderProgramAnnotation

	def codeName(self):
		return self.name

	def setCodeName(self, name):
		self.name = name

	def codeParameters(self):
		return self.codeparameters.codeParameters()

	def extractConstraints(self, ce):
		ce(self.vsCall)
		ce(self.fsCall)
		ce(self.junk)