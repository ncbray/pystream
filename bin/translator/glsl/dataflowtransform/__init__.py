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

def findIOTrees(context):
	
	compiler = context.compiler
	dioa = context.dioa
	code = context.code
	dataflow = context.dataflow
	
	trees = IOTrees()
	context.trees = trees
	
	# Find the inputs / uniforms
	# param 0  -> uniforms
	# param 1  -> context object
	# param 2+ -> inputs
			
	params     = code.codeparameters.params		
	lut        = dataflow.entry.modifies
	exist      = dataflow.entry.annotation.mask
	contextObj = iotree.getSingleObject(dioa, lut, params[1])
	
	trees.uniformIn = iotree.evaluateLocal(dioa, lut, exist, params[0], 'uniform')
	trees.contextIn = iotree.evaluateContextObject(dioa, lut, exist, params[1], contextObj, 'in')
	trees.inputs    = [iotree.evaluateLocal(dioa, lut, exist, p, 'in') for p in params[2:]]
	
	# Find the outputs
	lut   = dataflow.exit.reads
	exist = dataflow.exit.annotation.mask
	
	# Context object
	trees.contextOut = iotree.evaluateContextObject(dioa, lut, exist, params[1], contextObj, 'out')
	
	# Return values
	returns = code.codeparameters.returnparams
	assert len(returns) == 1, returns
	trees.returnOut = iotree.evaluateLocal(dioa, lut, exist, returns[0], 'out')
	
	# Find the builtin fields
	trees.match(makePathMatcher(compiler))
	
	# Transform the trees
	# NOTE the output is done first, as it references a local which 
	# will later be transformed / eliminated by the input transform.
	
	def transformOutput(context, tree, lut):
		node = lut[tree.impl]
		iotransform.transformOutput(context.compiler, context.dioa, context.dataflow, tree, node)

	def transformInput(context, tree, lut):
		node = lut[tree.impl]
		iotransform.transformInput(context.compiler, context.dioa, context.dataflow, tree, node)

	
	### OUTPUT ###
	# Transform the output context object
	transformOutput(context, trees.contextOut, dataflow.entry.modifies)

	# Transform the return value
	transformOutput(context, trees.returnOut, dataflow.exit.reads)
	
	### INPUT ###
	# Transform self
	transformInput(context, trees.uniformIn, dataflow.entry.modifies)
	
	# Transform input context object
	transformInput(context, trees.contextIn, dataflow.entry.modifies)

	# Transform the input parameters
	for tree in trees.inputs:
		transformInput(context, tree, dataflow.entry.modifies)	
	
	iotransform.killNonintrinsicIO(compiler, dataflow)
	trees.buildLUTs()
	
def harmonizeUniformTrees(name, uid, tree0, tree1):
	nodename = "%s_%d"  % (name, uid)
	uid += 1

	tree0.name = nodename
	tree1.name = nodename

	for field in tree0.fields.iterkeys():
		if field not in tree1.fields: continue
		print "HARMONIZE", field
		uid = harmonizeUniformTrees(name, uid, tree0.fields[field], tree1.fields[field])

	return uid

class IOTrees(object):
	def __init__(self):
		self.uniformIn = None
		self.contextIn = None
		self.inputs  = None

		self.contextOut = None
		self.returnOut  = None

		self.inputLUT = {}
		self.outputLUT = {}

	def match(self, matcher):
		self.contextIn.match(matcher)
		self.contextOut.match(matcher)

	def buildLUTs(self):
		self.inputLUT = {}
		self.uniformIn.buildImplementationLUT(self.inputLUT)
		self.contextIn.buildImplementationLUT(self.inputLUT)
		for inp in self.inputs:
			inp.buildImplementationLUT(self.inputLUT)
		
		self.outputLUT = {}
		self.contextOut.buildImplementationLUT(self.outputLUT)
		self.returnOut.buildImplementationLUT(self.outputLUT)
		

class DataflowTransformContext(object):
	def __init__(self, compiler, code):
		self.compiler = compiler
		self.code     = code
	
	def convert(self):
		self.dataflow = analysis.dataflowIR.convert.evaluateCode(self.compiler, self.code)
	
	def analyze(self):
		self.dioa = correlatedanalysis.evaluateDataflow(self.compiler, self.dataflow)
		self.dataflow = self.dioa.flat
		
		findIOTrees(self)

	def synthesize(self):
		# Reconstruct the CFG from the dataflow graph
		self.cfg = dataflowsynthesis.process(self.compiler, self.dataflow, self.code.codeName(), dump=True)

		# Find pools
		self.pa = poolanalysis.process(self.compiler, self.dataflow, self.dioa)
	
		# Translate CFG + pools into GLSL
		glsltranslator.process(self)
		
	def dump(self):
		self.dioa.debugDump(self.code.codeName())
		analysis.dataflowIR.dump.evaluateDataflow(self.dataflow, 'summaries\dataflow', self.code.codeName())

	def uniformTree(self):
		return self.trees.uniformIn

	def simplify(self):
		loadelimination.evaluateDataflow(self.dataflow)
		dce.evaluateDataflow(self.dataflow)

	def splitTuple(self, tree):
		indexLUT = {}
		for field, node in tree.fields.iteritems():
			if field.type == 'Array':
				index = field.name.pyobj
				indexLUT[index] = node		
		return [indexLUT[i] for i in range(len(indexLUT))]

	def link(self, other):
		# Break apart the output tuple.
		outputs = self.splitTuple(self.trees.returnOut)
		inputs  = other.trees.inputs
		
		assert len(inputs) == len(outputs), "I/O mismatch" 
		
		uid = 0
		for outp, inp in zip(outputs, inputs):
			uid = outp.makeLinks(inp, uid)
		

def evaluateCode(compiler, vscode, fscode):
	vscontext = DataflowTransformContext(compiler, vscode)
	fscontext = DataflowTransformContext(compiler, fscode)

	with compiler.console.scope('convert'):
		vscontext.convert()
		fscontext.convert()

	with compiler.console.scope('analyze'):
		vscontext.analyze()
		fscontext.analyze()

	with compiler.console.scope('link'):
		harmonizeUniformTrees('common', 0, vscontext.uniformTree(), fscontext.uniformTree())
		vscontext.link(fscontext)
		
		iotransform.killUnusedOutputs(fscontext)
		fscontext.simplify()
		
		# TODO load eliminate uniform -> varying
		# TODO propagate DCE between shaders

		iotransform.killUnusedOutputs(vscontext)
		vscontext.simplify()

	with compiler.console.scope('synthesize'):
		vscontext.synthesize()
		fscontext.synthesize()

	with compiler.console.scope('dump'):
		vscontext.dump()
		fscontext.dump()
