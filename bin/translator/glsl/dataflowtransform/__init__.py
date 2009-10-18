import analysis.dataflowIR.dump
import analysis.dataflowIR.convert
from analysis.dataflowIR.transform import loadelimination
from analysis.dataflowIR.transform import dce

import translator.glsl.dataflowtransform.correlatedanalysis

from . import poolanalysis
from analysis.cfgIR import dataflowsynthesis
from . import glsltranslator

from . import iotree
from . import iotransform

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

def findIOTrees(compiler, dioa, code, dataflow):
		# Find the inputs / uniforms
		# param 0  -> uniforms
		# param 1  -> context object
		# param 2+ -> inputs
		
		matcher = makePathMatcher(compiler)
				
		params     = code.codeparameters.params		
		lut        = dataflow.entry.modifies
		exist      = dataflow.entry.annotation.mask
		contextObj = iotree.getSingleObject(dioa, lut, params[1])

		uniforms = iotree.evaluateLocal(dioa, lut, exist, params[0], 'uniform')
		cin      = iotree.evaluateContextObject(dioa, lut, exist, contextObj, 'in')
		inputs   = [iotree.evaluateLocal(dioa, lut, exist, p, 'in') for p in params[2:]]

		# Find the outputs
		lut   = dataflow.exit.reads
		exist = dataflow.exit.annotation.mask

		# Context object
		cout = iotree.evaluateContextObject(dioa, lut, exist, contextObj, 'out')
		
		# Return values
		returns = code.codeparameters.returnparams
		assert len(returns) == 1, returns
		rout = iotree.evaluateLocal(dioa, lut, exist, returns[0], 'out')

		# Find the builtin fields
		cin.match(matcher)
		cout.match(matcher)
		
		# Tranform the context object
		coutNode = dataflow.entry.modifies[params[1]]
		iotransform.transformOutput(compiler, dioa, dataflow, cout, coutNode)
		
		# Transform the return value
		routNode = dataflow.exit.reads[returns[0]]
		iotransform.transformOutput(compiler, dioa, dataflow, rout, routNode)
		
		
		iotransform.killNonintrinsicIO(compiler, dataflow)
		
		loadelimination.evaluateDataflow(dataflow)
		dce.evaluateDataflow(dataflow)
		
		return uniforms, inputs, cin, cout

def evaluateCode(compiler, code):
	with compiler.console.scope('convert'):
		dataflow = analysis.dataflowIR.convert.evaluateCode(compiler, code)

	with compiler.console.scope('analyze'):
		dioa = translator.glsl.dataflowtransform.correlatedanalysis.evaluateDataflow(compiler, dataflow)
		dataflow = dioa.flat

		findIOTrees(compiler, dioa, code, dataflow)

		# Reconstruct the CFG from the dataflow graph
		cfg = dataflowsynthesis.process(compiler, dataflow, code.codeName(), dump=True)

		# Find pools
		pa = poolanalysis.process(compiler, dataflow, dioa)
	
		# Translate CFG + pools into GLSL
		glsltranslator.process(compiler, code, cfg, pa)

	with compiler.console.scope('dump'):
		dioa.debugDump(code.codeName())
		analysis.dataflowIR.dump.evaluateDataflow(dataflow, 'summaries\dataflow', code.codeName())
