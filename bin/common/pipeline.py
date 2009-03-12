import time
import util

import analysis.cpa
import analysis.lifetimeanalysis
import analysis.dump.dumpreport

import analysis.shape

import optimization.methodcall
from optimization.cullprogram import cullProgram
from optimization.simplify import simplify
from optimization.clone import clone
from optimization.callconverter import callConverter
from optimization.argumentnormalization import normalizeArguments
from optimization.codeinlining import inlineCode


def codeConditioning(console, extractor, entryPoints, dataflow):
	db = dataflow.db

	console.begin('conditioning')

	if True:
		# Try to identify and optimize method calls
		console.begin('method call')
		optimization.methodcall.methodCall(console, extractor, db)
		console.end()

	lifetimeAnalysis(console, dataflow)

	if True:
		# Fold, DCE, etc.
		console.begin('simplify')
		for code in db.liveFunctions():
			if not code.annotation.descriptive:
				simplify(extractor, db, code)
		console.end()

	if True:
		# Seperate different invocations of the same code.
		console.begin('clone')
		clone(console, extractor, entryPoints, db)
		console.end()

	if True:
		# Try to eliminate kwds, vargs, kargs, and default arguments.
		console.begin('argument normalization')
		normalizeArguments(dataflow, db)
		console.end()

	if True:
		# Try to eliminate trivial functions.
		console.begin('code inlining')
		inlineCode(dataflow, entryPoints, db)
		console.end()

	console.end()

def lifetimeAnalysis(console, dataflow):
	console.begin('lifetime analysis')
	la = analysis.lifetimeanalysis.LifetimeAnalysis()
	la.process(dataflow.db.liveCode)
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


def shapePass(console, e, result, entryPoints):
	if False:
		import scriptsetup
		def f():
			analysis.shape.evaluate(console, e, result, entryPoints)
		scriptsetup.profile(f)
	else:
		analysis.shape.evaluate(console, e, result, entryPoints)


def cpaDump(console, name, e, result, entryPoints):
	console.begin('dump')
	analysis.dump.dumpreport.dump(name, e, result, entryPoints)
	console.end()

def cull(console, entryPoints, db):
	console.begin('cull')
	cullProgram(entryPoints, db)
	console.end()

def evaluate(console, name, e, entryPoints):
	console.begin('compile')
	result = cpaPass(console, e, entryPoints)

	# Get rid of dead functions/contexts
	cull(console, entryPoints, result.db)

	if False:
		result = cpaPass(console, e, entryPoints)

	# HACK rerun lifetime analysis, as inlining causes problems.
	lifetimeAnalysis(console, result)

	try:
		shapePass(console, e, result, entryPoints)

	finally:
		cpaDump(console, name, e, result, entryPoints)

	console.end()