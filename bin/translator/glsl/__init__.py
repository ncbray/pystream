from . shadertranslator import GLSLTranslator
from language.glsl import codegen

from . pythonshader import PythonShader

def translate(console, dataflow, interface):
	console.begin('translate to glsl')

	try:
		translator = GLSLTranslator(intrinsics.makeIntrinsicRewriter(dataflow.extractor))
		cg = codegen.GLSLCodeGen()

		for code in interface.entryCode():
			console.output(str(code))

			shader = PythonShader(code)

			# HACK fixed frequency annotations for parameters.
			shader.frequency[code.parameters[0]] = 'uniform'
			for p in code.parameters[1:]:
				shader.frequency[p] = 'input'

			iotransform.evaluateShader(console, dataflow, shader)

			result = translator.processShader(shader)
			print cg(result)
			print
	finally:
		console.end()