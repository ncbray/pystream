import analysis.dataflowIR.dump
import analysis.dataflowIR.convert
import translator.glsl.dataflowtransform.correlatedanalysis

from . import poolanalysis
from analysis.cfgIR import dataflowsynthesis
from . import glsltranslator


def evaluateCode(compiler, code):
	with compiler.console.scope('convert'):
		dataflow = analysis.dataflowIR.convert.evaluateCode(compiler, code)

	with compiler.console.scope('analyze'):
		dioa = translator.glsl.dataflowtransform.correlatedanalysis.evaluateDataflow(compiler, dataflow)

		# Reconstruct the CFG from the dataflow graph
		cfg = dataflowsynthesis.process(compiler, dataflow, code.codeName(), dump=True)

		# Find pools
		pa = poolanalysis.process(compiler, dataflow, dioa)
	
		# Translate CFG + pools into GLSL
		glsltranslator.process(compiler, code, cfg, dioa, pa)

	with compiler.console.scope('dump'):
		dioa.debugDump(code.codeName())
		analysis.dataflowIR.dump.evaluateDataflow(dataflow, 'summaries\dataflow', code.codeName())
