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
import optimization.loadelimination
import optimization.storeelimination

import translator.glsl

def codeConditioning(console, extractor, interface, dataflow):
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
		clone(console, extractor, interface, db)
		console.end()

	if True:
		# Try to eliminate kwds, vargs, kargs, and default arguments.
		console.begin('argument normalization')
		normalizeArguments(dataflow, db)
		console.end()

	if True:
		# Try to eliminate trivial functions.
		console.begin('code inlining')
		inlineCode(dataflow, interface, db)
		console.end()

		# Get rid of dead functions/contexts
		cull(console, interface, db)

	if True:
		optimization.loadelimination.evaluate(console, dataflow)

	if True:
		optimization.storeelimination.evaluate(console, dataflow)


	console.end()

def lifetimeAnalysis(console, dataflow):
	console.begin('lifetime analysis')
	la = analysis.lifetimeanalysis.LifetimeAnalysis()
	la.process(dataflow.db.liveCode)
	console.end()

def cpaAnalyze(console, e, interface, opPathLength=0):
	console.begin('cpa analysis')
	result = analysis.cpa.evaluate(console, e, interface, opPathLength)
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

def cpaPass(console, e, interface, opPathLength=0):
	console.begin('depython')
	result = cpaAnalyze(console, e, interface, opPathLength)
	codeConditioning(console, e, interface, result)
	console.end()
	return result


def shapePass(console, e, result, interface):
	analysis.shape.evaluate(console, e, result, interface)


def cpaDump(console, name, e, result, interface):
	console.begin('dump')
	analysis.dump.dumpreport.dump(name, e, result, interface)
	console.end()

def cull(console, interface, db):
	console.begin('cull')
	cullProgram(interface, db)
	console.end()

def evaluate(console, name, extractor, interface):
	console.begin('compile')
	result = cpaPass(console, extractor, interface)

	if True:
		# Intrinsics can prevent complete exhaustive inlining.
		# Adding call-path sensitivity compensates.
		result = cpaPass(console,  extractor, interface, 3)

	# HACK rerun lifetime analysis, as inlining causes problems for the function annotations.
	lifetimeAnalysis(console, result)

	try:
		if False:
			shapePass(console, extractor, result, interface)

		if True:
			translator.glsl.translate(console, result, interface)
	finally:
		cpaDump(console, name, extractor, result, interface)

	console.end()