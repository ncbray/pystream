import analysis.dataflowIR.dump
import analysis.dataflowIR.convert
import translator.glsl.dataflowtransform.correlatedanalysis

from . import poolanalysis
from analysis.cfgIR import dataflowsynthesis
from . import glsltranslator

from . import iotree

def evaluateCode(compiler, code):
	with compiler.console.scope('convert'):
		dataflow = analysis.dataflowIR.convert.evaluateCode(compiler, code)

	with compiler.console.scope('analyze'):
		dioa = translator.glsl.dataflowtransform.correlatedanalysis.evaluateDataflow(compiler, dataflow)

		# Find the inputs / uniforms
		# param 0  -> uniforms
		# param 1  -> context object
		# param 2+ -> inputs
		params = code.codeparameters.params		
		lut      = dataflow.entry.modifies
		contextObj = iotree.getSingleObject(dioa, lut, params[1])

		uniforms = iotree.evaluateLocal(dioa, lut, params[0])
		cin      = iotree.evaluateContextObject(dioa, lut, contextObj)
		inputs   = [iotree.evaluateLocal(dioa, lut, p) for p in params[2:]]

		# Find the outputs
		lut  = dataflow.exit.reads
		cout = iotree.evaluateContextObject(dioa, lut, contextObj)

		# Reconstruct the CFG from the dataflow graph
		cfg = dataflowsynthesis.process(compiler, dataflow, code.codeName(), dump=True)

		# Find pools
		pa = poolanalysis.process(compiler, dataflow, dioa)
	
		# Translate CFG + pools into GLSL
		glsltranslator.process(compiler, code, cfg, dioa, pa)

	with compiler.console.scope('dump'):
		dioa.debugDump(code.codeName())
		analysis.dataflowIR.dump.evaluateDataflow(dataflow, 'summaries\dataflow', code.codeName())
