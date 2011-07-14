# Copyright 2011 Nicholas Bray
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time
import util

#import analysis.ipa
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

from . import errors

import stats.shader

def codeConditioning(compiler, prgm, firstPass, dumpStats=False):
	with compiler.console.scope('conditioning'):
		if firstPass:
			# Try to identify and optimize method calls
			optimization.methodcall.evaluate(compiler, prgm)

		analysis.lifetimeanalysis.evaluate(compiler, prgm)

		if True:
			# Fold, DCE, etc.
			optimization.simplify.evaluate(compiler, prgm)

		if firstPass and dumpStats:
			stats.contextStats(compiler, prgm, 'optimized', classOK=True)


		if firstPass:
			# Separate different invocations of the same code.
			optimization.clone.evaluate(compiler, prgm)

		if firstPass and dumpStats:
			stats.contextStats(compiler, prgm, 'clone', classOK=True)


		if firstPass:
			# Try to eliminate kwds, vargs, kargs, and default arguments.
			# Done before inlining, as the current implementation of inlining
			# Cannot deal with complex calling conventions.
			optimization.argumentnormalization.evaluate(compiler, prgm)

		if firstPass:
			# Try to eliminate trivial functions.
			optimization.codeinlining.evaluate(compiler, prgm)

			# Get rid of dead functions/contexts
			optimization.cullprogram.evaluate(compiler, prgm)


		if True:
			optimization.loadelimination.evaluate(compiler, prgm)

		if True:
			optimization.storeelimination.evaluate(compiler, prgm)

		if firstPass and dumpStats:
			stats.contextStats(compiler, prgm, 'inline')

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
		#analysis.ipa.evaluate(compiler, prgm)
		#assert False, "abort"

		analysis.cpa.evaluate(compiler, prgm, opPathLength, firstPass=firstPass)

		if firstPass:
			stats.contextStats(compiler, prgm, 'firstpass' if firstPass else 'secondpass', classOK=firstPass)
		#errors.abort("testing")

		codeConditioning(compiler, prgm, firstPass, firstPass)


def evaluate(compiler, prgm, name):
	try:
		with compiler.console.scope('compile'):
			try:
				# First compiler pass
				depythonPass(compiler, prgm)

				if True:
					# Second compiler pass
					# Intrinsics can prevent complete exhaustive inlining.
					# Adding call-path sensitivity compensates.
					depythonPass(compiler, prgm, 3, firstPass=False)
				else:
					# HACK rerun lifetime analysis, as inlining causes problems for the function annotations.
					analysis.lifetimeanalysis.evaluate(compiler, prgm)

				stats.contextStats(compiler, prgm, 'secondpass')

				#errors.abort('test')

				if True:
					# Translate abstract shader programs into code.
					translator.dataflowtransform.translate(compiler, prgm)

					if config.dumpStats:
						stats.shader.digest(compiler)
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
	except errors.CompilerAbort, e:
		print
		print "ABORT", e
