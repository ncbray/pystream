from . shadertranslator import GLSLTranslator
from language.glsl import codegen

from . pythonshader import PythonShader

def translate(console, dataflow, interface):
	console.begin('translate to glsl')

	try:
		translator = GLSLTranslator(intrinsics.makeIntrinsicRewriter(dataflow.extractor))

		for code in interface.entryCode():
			console.output(str(code))

			shader = PythonShader(code)

			iotransform.evaluateShader(console, dataflow, shader)

			result = translator.processShader(shader)

			cg = codegen.GLSLCodeGen()
			print cg(result)
			print
	finally:
		console.end()