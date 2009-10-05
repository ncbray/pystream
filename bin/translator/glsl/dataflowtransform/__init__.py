import analysis.dataflowIR.dump
import analysis.dataflowIR.convert
import translator.glsl.dataflowtransform.correlatedanalysis

from . import poolanalysis
from analysis.cfgIR import dataflowsynthesis
from . import glsltranslator

from . import iotree

def makePathMatcher(compiler):
	root = {}
	for path, name, input, output in compiler.interface.glsl.attr:
		current = root

		#path = reverse(path)		
		for part in path[:-1]:
			if part not in current:
				current[part] = {}
			current = current[part]

		current[path[-1]] = name

	return root

def evaluateCode(compiler, code):
	with compiler.console.scope('convert'):
		dataflow = analysis.dataflowIR.convert.evaluateCode(compiler, code)

	with compiler.console.scope('analyze'):
		dioa = translator.glsl.dataflowtransform.correlatedanalysis.evaluateDataflow(compiler, dataflow)

		# Find the inputs / uniforms
		# param 0  -> uniforms
		# param 1  -> context object
		# param 2+ -> inputs
		
		matcher = makePathMatcher(compiler)
				
		params = code.codeparameters.params		
		lut      = dataflow.entry.modifies
		exist    = dioa.opMask(dataflow.entry)
		contextObj = iotree.getSingleObject(dioa, lut, params[1])

		uniforms = iotree.evaluateLocal(dioa, lut, exist, params[0], 'uniform')
		cin      = iotree.evaluateContextObject(dioa, lut, exist, contextObj, 'in')
		inputs   = [iotree.evaluateLocal(dioa, lut, exist, p, 'in') for p in params[2:]]

		# Find the outputs
		lut  = dataflow.exit.reads
		exist = dioa.opMask(dataflow.exit)

		cout = iotree.evaluateContextObject(dioa, lut, exist, contextObj, 'out')

		# Find the builtin fields
		cin.match(matcher)
		cout.match(matcher)

		# Reconstruct the CFG from the dataflow graph
		cfg = dataflowsynthesis.process(compiler, dataflow, code.codeName(), dump=True)

		# Find pools
		pa = poolanalysis.process(compiler, dataflow, dioa)
	
		# Translate CFG + pools into GLSL
		glsltranslator.process(compiler, code, cfg, dioa, pa)

	with compiler.console.scope('dump'):
		dioa.debugDump(code.codeName())
		analysis.dataflowIR.dump.evaluateDataflow(dataflow, 'summaries\dataflow', code.codeName())
