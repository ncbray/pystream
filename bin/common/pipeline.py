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
		clone(console, extractor, interface.entryPoint, db)
		console.end()

	if True:
		# Try to eliminate kwds, vargs, kargs, and default arguments.
		console.begin('argument normalization')
		normalizeArguments(dataflow, db)
		console.end()

	if True:
		# Try to eliminate trivial functions.
		console.begin('code inlining')
		inlineCode(dataflow, interface.entryPoint, db)
		console.end()

		# Get rid of dead functions/contexts
		cull(console, interface.entryPoint, db)

	if True:
		optimization.loadelimination.evaluate(console, dataflow, interface.entryPoint)

	if True:
		optimization.storeelimination.evaluate(console, dataflow, interface.entryPoint)


	console.end()

def lifetimeAnalysis(console, dataflow):
	console.begin('lifetime analysis')
	la = analysis.lifetimeanalysis.LifetimeAnalysis()
	la.process(dataflow.db.liveCode)
	console.end()

def cpaAnalyze(console, e, interface):
	console.begin('cpa analysis')
	result = analysis.cpa.evaluate(console, e, interface)
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

def cpaPass(console, e, interface):
	console.begin('depython')
	result = cpaAnalyze(console, e, interface)
	codeConditioning(console, e, interface, result)
	console.end()
	return result


def shapePass(console, e, result, entryPoints):
#	import scriptsetup
#	def f():
#		analysis.shape.evaluate(console, e, result, entryPoints)
#	scriptsetup.profile(f)

	analysis.shape.evaluate(console, e, result, entryPoints)


def cpaDump(console, name, e, result, entryPoints):
	console.begin('dump')
	analysis.dump.dumpreport.dump(name, e, result, entryPoints)
	console.end()

def cull(console, entryPoints, db):
	console.begin('cull')
	cullProgram(entryPoints, db)
	console.end()

def evaluate(console, name, extractor, interface):
	entryPoints = interface.entryPoint
	attr        = interface.attr

	console.begin('compile')
	result = cpaPass(console, extractor, interface)

	if True:
		result = cpaPass(console,  extractor, interface)

	# HACK rerun lifetime analysis, as inlining causes problems for the function annotations.
	lifetimeAnalysis(console, result)

	try:
		if False:
			shapePass(console, extractor, result, entryPoints)

		if True:
			translator.glsl.translate(console, result, entryPoints)
	finally:
		cpaDump(console, name, extractor, result, entryPoints)

	console.end()