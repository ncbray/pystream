from analysis import astcollector
import collections
import config

from language.python import ast

from translator import intrinsics

from util.io.report import *

import os.path
from util.io.filesystem import ensureDirectoryExists


remap = {'Shader':'material', 'SkyBox':'skybox', 'SSAO':'ssao',
		'DirectionalBilateralBlur':'bilateral', 'AmbientPass':'ambient', 'LightPass':'light',
		'DirectionalBlur':'blur', 'RadialBlur':'post'}

shaderNames = ['material', 'skybox', 'ssao', 'bilateral', 'ambient', 'light', 'blur', 'post']

class ShaderStatCollector(object):
	def __init__(self):
		self.opCount = collections.defaultdict(lambda: 0)

	def op(self, op):
		opT = type(op)


		if isinstance(op, (ast.Load, ast.Store)) and intrinsics.isIntrinsicMemoryOp(op):
			name = "I"+opT.__name__
		else:
			name = opT.__name__

		self.opCount[name] += 1

	def copies(self, count):
		if count:
			name = 'CopyLocal'
			self.opCount[name] += count

def shaderStats(compiler, stage, name, vscontext, fscontext):
	collect = ShaderStatCollector()

	for code in (vscontext.code, fscontext.code):
		ops, lcls, copies = astcollector.getAll(code)

		for op in ops:
			collect.op(op)

		collect.copies(len(copies))

	name = remap[name]

	compiler.stats[stage][name] = collect


def functionRatios(collect, classOK):
	builder = TableBuilder('functions', '\%', 'contexts', '\%', 'ratio')
	builder.setFormats('%d', '%.1f', '%d', '%.1f', '%.1f')


	totalCode = 0
	totalContexts = 0

	for cls in classes:
		codeCount    = collect.codeCount[cls]
		contextCount = collect.contextCount[cls]

		totalCode += codeCount
		totalContexts += contextCount

	for cls in classes:
		codeCount    = collect.codeCount[cls]
		contextCount = collect.contextCount[cls]

		if classOK:
			builder.row(cls,
					codeCount, ratio(100.0*codeCount, totalCode),
					contextCount, ratio(100.0*contextCount, totalContexts),
					ratio(contextCount, codeCount))


	builder.row('total', totalCode, 100.0, totalContexts, 100.0, float(totalContexts)/totalCode)

	if not classOK: builder.rewrite(0, 2, 4)

	f = open(os.path.join(collect.reportdir, 'context-ratios.tex'), 'w')
	builder.dumpLatex(f, "%s-context-ratios" % collect.name)
	f.close()


def opTable(stage, lut):
	reportdir = os.path.join(config.outputDirectory, 'stats', stage)
	ensureDirectoryExists(reportdir)


	total = collections.defaultdict(lambda: 0)

	for shader, opLUT in lut.iteritems():
		for op, count in opLUT.opCount.iteritems():
			total[op] += count

	if False:
		opNames = []
		for op in asts:
			if total[op] > 0:
				opNames.append(op)
	else:
		opNames = ['DirectCall', 'Load', 'ILoad', 'Store', 'IStore', 'Allocate']

	builder = TableBuilder(*opNames)
	builder.setFormats(*(['%d']*len(opNames)))


	for shader in shaderNames:
		opLUT = lut[shader]
		builder.row(shader, *[opLUT.opCount[name] for name in opNames])

	builder.row('total', *[total[name] for name in opNames])


	f = open(os.path.join(reportdir, 'shader-ops.tex'), 'w')
	builder.dumpLatex(f, "%s-shader-ops" % stage)
	f.close()


def digest(compiler):

	for stage, lut in compiler.stats.iteritems():
		opTable(stage, lut)
