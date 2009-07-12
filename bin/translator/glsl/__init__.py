from . shadertranslator import GLSLTranslator
from language.glsl import codegen

from . pythonshader import PythonShaderProgram

from abstractcode.shaderprogram import ShaderProgram

from . import dataflowtransform

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
		pathMatcher = makePathMatcher(compiler.interface)

		translator = GLSLTranslator(intrinsics.makeIntrinsicRewriter(compiler.extractor))

		for code in compiler.interface.entryCode():
			if isinstance(code, ShaderProgram):
				vs = code.vertexShaderCode()
				fs = code.fragmentShaderCode()

				with compiler.console.scope('vs'):
					dataflowtransform.evaluateCode(compiler, vs)

				with compiler.console.scope('fs'):
					dataflowtransform.evaluateCode(compiler, fs)

				shader = PythonShaderProgram(vs, fs, pathMatcher)
				iotransform.evaluateShaderProgram(compiler, shader, pathMatcher)
				codes = translator.processShaderProgram(shader)

				for code in codes:
					print codegen.GLSLCodeGen()(code)
					print
					print
