from . shadertranslator import GLSLTranslator
from language.glsl import codegen

from . pythonshader import PythonShaderProgram

from abstractcode.shaderprogram import ShaderProgram

class CompilerContext(object):
	def __init__(self, console, extractor, interface):
		self.console   = console
		self.extractor = extractor
		self.interface = interface




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

def translate(console, extractor, interface):
	context = CompilerContext(console, extractor, interface)

	with context.console.scope('translate to glsl'):
		pathMatcher = makePathMatcher(context.interface)

		translator = GLSLTranslator(intrinsics.makeIntrinsicRewriter(context.extractor))

		for code in context.interface.entryCode():
			if isinstance(code, ShaderProgram):
				vs = code.vertexShaderCode()
				fs = code.fragmentShaderCode()

				shader = PythonShaderProgram(vs, fs, pathMatcher)
				iotransform.evaluateShaderProgram(context, shader, pathMatcher)
				codes = translator.processShaderProgram(shader)

				for code in codes:
					print codegen.GLSLCodeGen()(code)
					print
					print
