import time
import util

import analysis.cpa
import analysis.lifetimeanalysis
import analysis.dump.dumpreport
import analysis.programculler

import analysis.shape

import optimization.methodcall
import optimization.cullprogram
import optimization.simplify
import optimization.clone
import optimization.argumentnormalization
import optimization.codeinlining
import optimization.loadelimination
import optimization.storeelimination

import analysis.fsdf
import translator.dataflowtransform

import config
import threading

def codeConditioning(compiler):
	with compiler.console.scope('conditioning'):
		if True:
			# Try to identify and optimize method calls
			optimization.methodcall.evaluate(compiler)

		analysis.lifetimeanalysis.evaluate(compiler)

		if True:
			# Fold, DCE, etc.
			optimization.simplify.evaluate(compiler)

		if True:
			# Seperate different invocations of the same code.
			 optimization.clone.evaluate(compiler)

		if True:
			# Try to eliminate kwds, vargs, kargs, and default arguments.
			optimization.argumentnormalization.evaluate(compiler)

		if True:
			# Try to eliminate trivial functions.
			optimization.codeinlining.evaluate(compiler)

			# Get rid of dead functions/contexts
			optimization.cullprogram.evaluate(compiler)

		if True:
			optimization.loadelimination.evaluate(compiler)

		if True:
			optimization.storeelimination.evaluate(compiler)

		# HACK read/modify information is imprecise, so keep re-evaluating it
		# basically, DCE improves read modify information, which in turn allows better DCE
		# NOTE that this doesn't work very well without path sensitivity
		# "modifies" are quite imprecise without it, hence DCE doesn't do much.
		if False:
			bruteForceSimplification(compiler)


def bruteForceSimplification(compiler):
	with compiler.console.scope('brute force'):
		for i in range(2):
			analysis.lifetimeanalysis.evaluate(compiler)
			optimization.simplify.evaluate(compiler)


def depythonPass(compiler, opPathLength=0, firstPass=True):
	with compiler.console.scope('depython'):
		analysis.cpa.evaluate(compiler, opPathLength, firstPass=firstPass)
		codeConditioning(compiler)


def evaluate(compiler, name):
	with compiler.console.scope('compile'):
		try:
			# First compiler pass
			depythonPass(compiler)

			if True:
				# Second compiler pass
				# Intrinsics can prevent complete exhaustive inlining.
				# Adding call-path sensitivity compensates.
				depythonPass(compiler, 3, firstPass=False)

			if True:
				# HACK rerun lifetime analysis, as inlining causes problems for the function annotations.
				analysis.lifetimeanalysis.evaluate(compiler)

			if False:
				analysis.shape.evaluate(compiler)

			if False:
				analysis.fsdf.evaluate(compiler)

			if True:
				# Translate abstract shader programs into code.
				translator.dataflowtransform.translate(compiler)
		finally:
			if config.doDump:
				try:
					analysis.dump.dumpreport.evaluate(compiler, name)
				except Exception, e:
					# HACK prevents it from masking any exception that was thrown before.
					print "Exception dumping the report: ", e

			if config.doThreadCleanup:
				if threading.activeCount() > 1:
					with compiler.console.scope('threading cleanup'):
						compiler.console.output('Threads: %d' % (threading.activeCount()-1))
						for t in threading.enumerate():
							if t is not threading.currentThread():
								compiler.console.output('.')
								t.join()
