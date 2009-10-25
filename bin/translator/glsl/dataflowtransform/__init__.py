import analysis.dataflowIR.dump
import analysis.dataflowIR.convert
from analysis.dataflowIR.transform import loadelimination
from analysis.dataflowIR.transform import dce

from  translator.glsl.dataflowtransform import correlatedanalysis

from . import poolanalysis
from analysis.cfgIR import dataflowsynthesis
from . import glsltranslator

from . import iotree
from . import iotransform
import analysis.dataflowIR.convert

def makePathMatcher(compiler):
	root = {}
	for path, name, _input, _output in compiler.interface.glsl.attr:
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
	
	# Transform the trees
	# NOTE the output is done first, as it references a local which 
	# will later be transformed / eliminated by the input transform.
		
	### OUTPUT ###
	# Transform the output context object
	coutNode = dataflow.entry.modifies[params[1]]
	iotransform.transformOutput(compiler, dioa, dataflow, cout, coutNode)
	
	# Transform the return value
	routNode = dataflow.exit.reads[returns[0]]
	iotransform.transformOutput(compiler, dioa, dataflow, rout, routNode)
	
	### INPUT ###
	# Transform self
	uniformsNode = dataflow.entry.modifies[params[0]]
	iotransform.transformInput(compiler, dioa, dataflow, uniforms, uniformsNode)
	
	# Transform input context object
	cinNode = dataflow.entry.modifies[params[1]]
	iotransform.transformInput(compiler, dioa, dataflow, cin, cinNode)
	
	for p, tree in zip(params[2:], inputs):
		pNode = dataflow.entry.modifies[p]	
		iotransform.transformInput(compiler, dioa, dataflow, tree, pNode)
	
	
	iotransform.killNonintrinsicIO(compiler, dataflow)
	
	loadelimination.evaluateDataflow(dataflow)
	dce.evaluateDataflow(dataflow)
	
	inputLUT = {}
	uniforms.buildImplementationLUT(inputLUT)
	cin.buildImplementationLUT(inputLUT)
	for input in inputs:
		input.buildImplementationLUT(inputLUT)
	
	outputLUT = {}
	cout.buildImplementationLUT(outputLUT)
	rout.buildImplementationLUT(outputLUT)
	
	return inputLUT, outputLUT

def evaluateCode(compiler, code):
	with compiler.console.scope('convert'):
		dataflow = analysis.dataflowIR.convert.evaluateCode(compiler, code)

	with compiler.console.scope('analyze'):
		dioa = correlatedanalysis.evaluateDataflow(compiler, dataflow)
		dataflow = dioa.flat

		inputLUT, outputLUT = findIOTrees(compiler, dioa, code, dataflow)

		# Reconstruct the CFG from the dataflow graph
		cfg = dataflowsynthesis.process(compiler, dataflow, code.codeName(), dump=True)

		# Find pools
		pa = poolanalysis.process(compiler, dataflow, dioa)
	
		# Translate CFG + pools into GLSL
		glsltranslator.process(compiler, code, cfg, pa, inputLUT, outputLUT)

	with compiler.console.scope('dump'):
		dioa.debugDump(code.codeName())
		analysis.dataflowIR.dump.evaluateDataflow(dataflow, 'summaries\dataflow', code.codeName())
