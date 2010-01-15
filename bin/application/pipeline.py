import time
import util

import analysis.cpa
import analysis.lifetimeanalysis
import analysis.dump.dumpreport
import analysis.programculler

import optimization.methodcall
import optimization.cullprogram
import optimization.simplify
import optimization.clone
import optimization.argumentnormalization
import optimization.codeinlining
import optimization.loadelimination
import optimization.storeelimination

import translator.dataflowtransform

import config
import threading

def codeConditioning(compiler, prgm):
	with compiler.console.scope('conditioning'):
		if True:
			# Try to identify and optimize method calls
			optimization.methodcall.evaluate(compiler, prgm)

		analysis.lifetimeanalysis.evaluate(compiler, prgm)

		if True:
			# Fold, DCE, etc.
			optimization.simplify.evaluate(compiler, prgm)

		if True:
			# Separate different invocations of the same code.
			optimization.clone.evaluate(compiler, prgm)

		if True:
			# Try to eliminate kwds, vargs, kargs, and default arguments.
			# Done before inlining, as the current implementation of inlining
			# Cannot deal with complex calling conventions.
			optimization.argumentnormalization.evaluate(compiler, prgm)

		if True:
			# Try to eliminate trivial functions.
			optimization.codeinlining.evaluate(compiler, prgm)

		if True:
			# Get rid of dead functions/contexts
			optimization.cullprogram.evaluate(compiler, prgm)

		if True:
			optimization.loadelimination.evaluate(compiler, prgm)

		if True:
			optimization.storeelimination.evaluate(compiler, prgm)

		# HACK read/modify information is imprecise, so keep re-evaluating it
		# basically, DCE improves read modify information, which in turn allows better DCE
		# NOTE that this doesn't work very well without path sensitivity
		# "modifies" are quite imprecise without it, hence DCE doesn't do much.
		if False:
			bruteForceSimplification(compiler, prgm)


def bruteForceSimplification(compiler, prgm):
	with compiler.console.scope('brute force'):
		for _i in range(2):
			analysis.lifetimeanalysis.evaluate(compiler, prgm)
			optimization.simplify.evaluate(compiler, prgm)


def depythonPass(compiler, prgm, opPathLength=0, firstPass=True):
	with compiler.console.scope('depython'):
		analysis.cpa.evaluate(compiler, prgm, opPathLength, firstPass=firstPass)
		codeConditioning(compiler, prgm)


def evaluate(compiler, prgm, name):
	with compiler.console.scope('compile'):
		try:
			# First compiler pass
			depythonPass(compiler, prgm)

			if True:
				# Second compiler pass
				# Intrinsics can prevent complete exhaustive inlining.
				# Adding call-path sensitivity compensates.
				depythonPass(compiler, prgm, 3, firstPass=False)

			if True:
				# HACK rerun lifetime analysis, as inlining causes problems for the function annotations.
				analysis.lifetimeanalysis.evaluate(compiler, prgm)

			if True:
				# Translate abstract shader programs into code.
				translator.dataflowtransform.translate(compiler, prgm)
		finally:
			if config.doDump:
				try:
					analysis.dump.dumpreport.evaluate(compiler, prgm, name)
				except Exception, e:
					if config.maskDumpErrors:
						# HACK prevents it from masking any exception that was thrown before.
						print "Exception dumping the report: ", e
					else:
						raise

			if config.doThreadCleanup:
				if threading.activeCount() > 1:
					with compiler.console.scope('threading cleanup'):
						compiler.console.output('Threads: %d' % (threading.activeCount()-1))
						for t in threading.enumerate():
							if t is not threading.currentThread():
								compiler.console.output('.')
								t.join()
