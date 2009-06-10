import time
import util

import analysis.cpa
import analysis.lifetimeanalysis
import analysis.dump.dumpreport
import analysis.programculler

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

def codeConditioning(console, extractor, interface, storeGraph):
	with console.scope('conditioning'):
		liveCode, liveInvokes = analysis.programculler.findLiveFunctions(interface)

		if True:
			# Try to identify and optimize method calls
			optimization.methodcall.methodCall(console, extractor, storeGraph, liveCode)

		analysis.lifetimeanalysis.evaluate(console, interface, liveCode)

		if True:
			# Fold, DCE, etc.
			simplifyAll(console, extractor, storeGraph, liveCode)

		if True:
			# Seperate different invocations of the same code.
			liveCode = clone(console, extractor, interface, storeGraph)

		if True:
			# Try to eliminate kwds, vargs, kargs, and default arguments.
			with console.scope('argument normalization'):
				normalizeArguments(storeGraph, liveCode)

		if True:
			# Try to eliminate trivial functions.
			with console.scope('code inlining'):
				inlineCode(console, extractor, interface, storeGraph, liveCode)

			# Get rid of dead functions/contexts
			liveCode = cull(console, interface)

		if True:
			optimization.loadelimination.evaluate(console, extractor, storeGraph, liveCode)

		if True:
			changed = optimization.storeelimination.evaluate(console, extractor, storeGraph, liveCode)

		# HACK read/modify information is imprecise, so keep re-evaluating it
		# basically, DCE improves read modify information, which in turn allows better DCE
		# NOTE that this doesn't work very well without path sensitivity
		# "modifies" are quite imprecise without it, hence DCE doesn't do much.
		if False:
			bruteForceSimplification(console, extractor, interface, storeGraph, liveCode)

		return liveCode

def simplifyAll(console, extractor, storeGraph, liveCode):
	with console.scope('simplify'):
		changed = False
		for code in liveCode:
			if not code.annotation.descriptive:
				simplify(extractor, storeGraph, code)


def bruteForceSimplification(console, extractor, interface, storeGraph, liveCode):
	with console.scope('brute force'):
		for i in range(2):
			analysis.lifetimeanalysis.evaluate(console, interface, liveCode)
			simplifyAll(console, extractor, storeGraph, liveCode)




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

def cpaPass(console, extractor, interface, opPathLength=0, firstPass=True):
	with console.scope('depython'):
		result = cpaAnalyze(console, extractor, interface, opPathLength, firstPass=firstPass)
		liveCode = codeConditioning(console, extractor, interface, result.storeGraph)
		result.liveCode = liveCode # HACK for returning liveCode
		return result

def cpaDump(console, extractor, interface, name):
	analysis.dump.dumpreport.dump(console, extractor, interface, name)

def cull(console, interface):
	with console.scope('cull'):
		return cullProgram(interface)

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

			storeGraph = result.storeGraph
			liveCode   = result.liveCode

			if True:
				# HACK rerun lifetime analysis, as inlining causes problems for the function annotations.
				analysis.lifetimeanalysis.evaluate(console, interface, liveCode)

			if False:
				analysis.shape.evaluate(console, extractor, interface, storeGraph, liveCode)

			if True:
				# Translate abstract shader programs into code.
				translator.glsl.translate(console, extractor, interface)
		finally:
			if config.doDump:
				try:
					cpaDump(console, extractor, interface, name)
				except Exception, e:
					# HACK prevents it from masking any exception that was thrown before.
					print "Exception dumping the report: ", e