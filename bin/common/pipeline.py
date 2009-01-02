import time

import analysis.cpa
import analysis.cpa.lifetimeanalysis
import analysis.shape
#import analysis.fiapprox


def cpaHeader(uid):
	print
	print "============="
	print "=== CPA %d ===" % uid
	print "============="
	print

import optimization.methodcall
from optimization.cullprogram import cullProgram
from optimization.simplify import simplify
from optimization.clone import clone
from optimization.callconverter import callConverter

# HACK?
from stubs.stubcollector import descriptiveLUT

def codeConditioning(extractor, entryPoints, dataflow):
	print "Code conditioning"

	
	db = dataflow.db
	adb = analysis.cpa.CPAAnalysisDatabase(db)

	if True:
		print "Code conditioning: Method Call"
		optimization.methodcall.methodCall(extractor, adb)

	start = time.clock()
	print "Analysis: Object Lifetime"
	la =  analysis.cpa.lifetimeanalysis.LifetimeAnalysis()
	la.process(dataflow)
	dataflow.db.lifetime = la # HACK
	print "Analysis: %.2e" % (time.clock()-start)

	if True:
		print "Code conditioning: Simplify"
		live = db.liveFunctions()
		desc = extractor.desc
		newfuncs = [simplify(extractor, adb, func) if func not in descriptiveLUT and func in live else func for func in desc.functions]
		desc.functions = newfuncs

	if True:
		print "Code conditioning: Lower"
		# Flatten the interpreter calls.
		# Needs to be done before cloning, as cloning can only
		# redirect direct calls.
		for func in adb.liveFunctions():
			if not func in descriptiveLUT:
				callConverter(extractor, adb, func)

	if False:
		print "Code conditioning: Clone"
		clone(extractor, entryPoints, adb)

def cpaPass(e, entryPoints):
	print "Analyize"
	start = time.clock()
	result = analysis.cpa.evaluate(e, entryPoints)
	print "Analysis Time: %.3f" % (time.clock()-start)

	print
	start = time.clock()
	codeConditioning(e, entryPoints, result)
	print "Optimize: %.3f" % (time.clock()-start)

	return result

def cpaDump(e, result, entryPoints):
	print "Dump..."
	start = time.clock()
	analysis.cpa.dump(e, result, entryPoints)
	print "Dump: %.3f" % (time.clock()-start)


##def fiApproxPass(e, entryPoints):
##	print
##	print "==========================="
##	print "===== Analysis Pass 1 ====="
##	print "==========================="
##	print
##	
##	analysis.fiapprox.evaluate(self.moduleName, e, entryPoints, dumpFirst, False)
##
##	print
##	print "==========================="			
##	print "===== Analysis Pass 2 ====="
##	print "==========================="
##	print
##	
##	analysis.fiapprox.evaluate(self.moduleName, e, entryPoints, not dumpFirst, True)


def evaluate(e, entryPoints):
	cpaHeader(1)
	result = cpaPass(e, entryPoints)

	#analysis.shape.evaluate(e, entryPoints, result)

	if False:
		cpaHeader(2)
		result = cpaPass(e, entryPoints)

	cpaDump(e, result, entryPoints)
