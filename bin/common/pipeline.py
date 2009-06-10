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
			simplifyAll(console, extractor, db)

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
			changed = optimization.storeelimination.evaluate(console, dataflow)

		# HACK read/modify information is imprecise, so keep re-evaluating it
		# basically, DCE improves read modify information, which in turn allows better DCE
		# NOTE that this doesn't work very well without path sensitivity
		# "modifies" are quite imprecise without it, hence DCE doesn't do much.
		if True:
			bruteForceSimplification(console, extractor, interface, dataflow)

def simplifyAll(console, extractor, db):
	with console.scope('simplify'):
		changed = False
		for code in db.liveFunctions():
			if not code.annotation.descriptive:
				simplify(extractor, db, code)


def bruteForceSimplification(console, extractor, interface, dataflow):
	with console.scope('brute force'):
		for i in range(2):
			lifetimeAnalysis(console, dataflow, interface)
			simplifyAll(console, extractor, dataflow.db)


def lifetimeAnalysis(console, dataflow, interface):
	with console.scope('lifetime analysis'):
		la = analysis.lifetimeanalysis.LifetimeAnalysis(interface)
		la.process(dataflow.db.liveCode)

def cpaAnalyze(console, e, interface, opPathLength=0, firstPass=True):
	with console.scope('cpa analysis'):
		result = analysis.cpa.evaluate(console, e, interface, opPathLength, firstPass=firstPass)
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

def cpaPass(console, e, interface, opPathLength=0, firstPass=True):
	with console.scope('depython'):
		result = cpaAnalyze(console, e, interface, opPathLength, firstPass=firstPass)
		codeConditioning(console, e, interface, result)
	return result


def shapePass(console, e, result, interface):
	analysis.shape.evaluate(console, e, result, interface)


def cpaDump(console, extractor, interface, name):
	analysis.dump.dumpreport.dump(console, extractor, interface, name)

def cull(console, interface, db):
	with console.scope('cull'):
		cullProgram(interface, db)

def evaluate(console, name, extractor, interface):
	with console.scope('compile'):
		try:
			# First compiler pass
			result = cpaPass(console, extractor, interface)

			if True:
				# Second compiler pass
				# Intrinsics can prevent complete exhaustive inlining.
				# Adding call-path sensitivity compensates.
				result = cpaPass(console,  extractor, interface, 3, firstPass=False)

			if True:
				# HACK rerun lifetime analysis, as inlining causes problems for the function annotations.
				lifetimeAnalysis(console, result, interface)

			if False:
				shapePass(console, extractor, result, interface)

			if True:
				# Translate abstract shader programs into code.
				translator.glsl.translate(console, result, interface)
		finally:
			if config.doDump:
				cpaDump(console, extractor, interface, name)