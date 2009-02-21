import time

import analysis.cpa
import analysis.cpa.lifetimeanalysis
import analysis.cpa.analysisdatabase
import analysis.cpa.dumpreport
import analysis.shape
#import analysis.fiapprox

import util

import optimization.methodcall
from optimization.cullprogram import cullProgram
from optimization.simplify import simplify
from optimization.clone import clone
from optimization.callconverter import callConverter
from optimization.argumentnormalization import normalizeArguments
from optimization.codeinlining import inlineCode


def codeConditioning(console, extractor, entryPoints, dataflow):
	db = dataflow.db
	adb = analysis.cpa.analysisdatabase.CPAAnalysisDatabase(db)

	console.begin('conditioning')

	if True:
		console.begin('lower')
		# Flatten the interpreter calls.
		# Must be done before cloning, as cloning can only
		# redirect direct calls.
		for func in db.liveFunctions():
			callConverter(extractor, func)
		console.end()

	if True:
		# Try to identify and optimize method calls
		console.begin('method call')
		optimization.methodcall.methodCall(console, extractor, adb)
		console.end()

	console.begin('lifetime analysis')
	la =  analysis.cpa.lifetimeanalysis.LifetimeAnalysis()
	la.process(dataflow)
	dataflow.db.lifetime = la # HACK
	console.end()

	if True:
		# Fold, DCE, etc.
		console.begin('simplify')
		for code in db.liveFunctions():
			if not code.annotation.descriptive:
				simplify(extractor, adb, code)
		console.end()

	if True:
		# Seperate different invocations of the same code.
		console.begin('clone')
		clone(console, extractor, entryPoints, adb)
		console.end()

	if True:
		# Try to eliminate kwds, vargs, kargs, and default arguments.
		console.begin('argument normalization')
		normalizeArguments(dataflow, adb)
		console.end()

	if True:
		# Try to eliminate trivial functions.
		console.begin('code inlining')
		inlineCode(dataflow, entryPoints, adb)
		console.end()

	console.end()

def cpaAnalyze(console, e, entryPoints):
	console.begin('cpa analysis')
	result = analysis.cpa.evaluate(console, e, entryPoints)
	console.output('')
	console.output("Constraints:   %d" % len(result.constraints))
	console.output("Contexts:      %d" % len(result.liveContexts))
	console.output("Code:          %d" % len(result.liveCode))
	console.output("Contexts/Code: %.1f" % (float(len(result.liveContexts))/max(len(result.liveCode), 1)))
	console.output("Slot Memory:   %s" % util.memorySizeString(result.slotMemory()))
	console.output('')
	console.output("Decompile:     %s" % util.elapsedTimeString(result.decompileTime))
	console.output("Solve:         %s" % util.elapsedTimeString(result.solveTime))
	console.end()
	return result

def cpaPass(console, e, entryPoints):
	console.begin('depython')
	result = cpaAnalyze(console, e, entryPoints)
	codeConditioning(console, e, entryPoints, result)
	console.end()
	return result

def cpaDump(console, name, e, result, entryPoints):
	console.begin('dump')
	start = time.clock()
	analysis.cpa.dumpreport.dump(name, e, result, entryPoints)
	console.end()

def evaluate(console, name, e, entryPoints):
	console.begin('compile')
	result = cpaPass(console, e, entryPoints)

	#analysis.shape.evaluate(e, entryPoints, result)

	if False:
		result = cpaPass(console, e, entryPoints)

	cpaDump(console, name, e, result, entryPoints)
	console.end()