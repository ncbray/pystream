from analysis.cpa import simpleimagebuilder
from . entrypointbuilder import buildEntryPoint
from . dump import Dumper

from . ipanalysis import IPAnalysis

from . memory.extractorpolicy import ExtractorPolicy
from . memory.storegraphpolicy import DefaultStoreGraphPolicy

def dumpAnalysisResults(analysis):
	dumper = Dumper('summaries/ipa')

	dumper.index(analysis.contexts.values(), analysis.root)

	for context in analysis.contexts.itervalues():
		dumper.dumpContext(context)


def evaluateWithImage(compiler, prgm):
	with compiler.console.scope('ipa analysis'):
		analysis = IPAnalysis(compiler, prgm.storeGraph.canonical, ExtractorPolicy(compiler.extractor), DefaultStoreGraphPolicy(prgm.storeGraph))

		for ep, args in prgm.entryPoints:
			buildEntryPoint(analysis, ep, args)

		analysis.topDown()

		print "%5d code" % len(analysis.liveCode)
		print "%5d contexts" % len(analysis.contexts)
		print "%.2f ms decompile" % (analysis.decompileTime*1000.0)

	with compiler.console.scope('ipa dump'):
		dumpAnalysisResults(analysis)


def evaluate(compiler, prgm):
	simpleimagebuilder.build(compiler, prgm)
	result = evaluateWithImage(compiler, prgm)
	return result
