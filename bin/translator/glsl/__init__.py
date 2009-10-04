from language.python.shaderprogram import ShaderProgram
from . import dataflowtransform

# interface is compiler.iterface
def makePathMatcher(interface):
	root = {}
	for path, name, input, output in interface.glsl.attr:
		current = root
		for part in reversed(path[1:]):
			if part not in current:
				current[part] = {}
			current = current[part]

		current[path[0]] = name

	return root

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
