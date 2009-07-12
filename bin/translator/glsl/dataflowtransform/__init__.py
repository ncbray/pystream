import analysis.dataflowIR.dump
import analysis.dataflowIR.convert
import translator.glsl.dataflowtransform.correlatedanalysis

def evaluateCode(compiler, code):
	with compiler.console.scope('convert'):
		dataflow = analysis.dataflowIR.convert.evaluateCode(compiler, code)

	with compiler.console.scope('analyize'):
		translator.glsl.dataflowtransform.correlatedanalysis.evaluateDataflow(compiler, dataflow, code.codeName())

	with compiler.console.scope('dump'):
		analysis.dataflowIR.dump.evaluateDataflow(dataflow, 'summaries\dataflow', code.codeName())
