from language.python.shaderprogram import ShaderProgram
from . import dataflowtransform

def translate(compiler):
	with compiler.console.scope('translate to glsl'):
		for code in compiler.interface.entryCode():
			if isinstance(code, ShaderProgram):
				vs = code.vertexShaderCode()
				fs = code.fragmentShaderCode()

				with compiler.console.scope('vs'):
					dataflowtransform.evaluateCode(compiler, vs)

				with compiler.console.scope('fs'):
					dataflowtransform.evaluateCode(compiler, fs)
