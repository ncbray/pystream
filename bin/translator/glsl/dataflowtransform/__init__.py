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

class DataflowTransformContext(object):
	def __init__(self, compiler, code):
		self.compiler = compiler
		self.code     = code
	
	def convert(self):
		self.dataflow = analysis.dataflowIR.convert.evaluateCode(self.compiler, self.code)
	
	def analyze(self):
		self.dioa = correlatedanalysis.evaluateDataflow(self.compiler, self.dataflow)
		self.dataflow = self.dioa.flat
		
		self.inputLUT, self.outputLUT = findIOTrees(self.compiler, self.dioa, self.code, self.dataflow)

		# Find pools
		self.pa = poolanalysis.process(self.compiler, self.dataflow, self.dioa)

	def synthesize(self):
		# Reconstruct the CFG from the dataflow graph
		self.cfg = dataflowsynthesis.process(self.compiler, self.dataflow, self.code.codeName(), dump=True)
	
		# Translate CFG + pools into GLSL
		glsltranslator.process(self.compiler, self.code, self.cfg, self.pa, self.inputLUT, self.outputLUT)
		
		
		

	def dump(self):
		self.dioa.debugDump(self.code.codeName())
		analysis.dataflowIR.dump.evaluateDataflow(self.dataflow, 'summaries\dataflow', self.code.codeName())


def evaluateCode(compiler, vscode, fscode):
	vscontext = DataflowTransformContext(compiler, vscode)
	fscontext = DataflowTransformContext(compiler, fscode)

	with compiler.console.scope('convert'):
		vscontext.convert()
		fscontext.convert()

	with compiler.console.scope('analyze'):
		vscontext.analyze()
		fscontext.analyze()

	with compiler.console.scope('synthesize'):
		vscontext.synthesize()
		fscontext.synthesize()

	with compiler.console.scope('dump'):
		vscontext.dump()
		fscontext.dump()
