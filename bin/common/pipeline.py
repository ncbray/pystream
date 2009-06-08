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

import analysis.fsdf
import translator.glsl

import config

def codeConditioning(console, extractor, interface, dataflow):
	db = dataflow.db

	with console.scope('conditioning'):
		if True:
			# Try to identify and optimize method calls
			optimization.methodcall.methodCall(console, extractor, db)

		lifetimeAnalysis(console, dataflow, interface)

		if True:
			# Fold, DCE, etc.
			with console.scope('simplify'):
				for code in db.liveFunctions():
					if not code.annotation.descriptive:
						simplify(extractor, db, code)
		if True:
			# Seperate different invocations of the same code.
			clone(console, extractor, interface, db)

		if True:
			# Try to eliminate kwds, vargs, kargs, and default arguments.
			with console.scope('argument normalization'):
				normalizeArguments(dataflow, db)

		if True:
			# Try to eliminate trivial functions.
			with console.scope('code inlining'):
				inlineCode(console, dataflow, interface, db)

			# Get rid of dead functions/contexts
			cull(console, interface, db)

		if True:
			optimization.loadelimination.evaluate(console, dataflow)

		if True:
			optimization.storeelimination.evaluate(console, dataflow)

def lifetimeAnalysis(console, dataflow, interface):
	with console.scope('lifetime analysis'):
		la = analysis.lifetimeanalysis.LifetimeAnalysis(interface)
		la.process(dataflow.db.liveCode)

def cpaAnalyze(console, e, interface, opPathLength=0):
	with console.scope('cpa analysis'):
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
	return result

def cpaPass(console, e, interface, opPathLength=0):
	with console.scope('depython'):
		result = cpaAnalyze(console, e, interface, opPathLength)
		codeConditioning(console, e, interface, result)
	return result


def shapePass(console, e, result, interface):
	analysis.shape.evaluate(console, e, result, interface)


def cpaDump(console, name, e, result, interface):
	with console.scope('dump'):
		analysis.dump.dumpreport.dump(console, name, e, result, interface)

def cull(console, interface, db):
	with console.scope('cull'):
		cullProgram(interface, db)

def evaluate(console, name, extractor, interface):
	with console.scope('compile'):
		result = cpaPass(console, extractor, interface)

		if False:
			# Intrinsics can prevent complete exhaustive inlining.
			# Adding call-path sensitivity compensates.
			result = cpaPass(console,  extractor, interface, 3)

		# HACK rerun lifetime analysis, as inlining causes problems for the function annotations.
		lifetimeAnalysis(console, result, interface)

		try:
			if False:
				shapePass(console, extractor, result, interface)

			if True:
				pass #translator.glsl.translate(console, result, interface)
		finally:
			if config.doDump:
				cpaDump(console, name, extractor, result, interface)