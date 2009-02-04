import time

import analysis.cpa
import analysis.cpa.lifetimeanalysis
import analysis.cpa.analysisdatabase
import analysis.cpa.dumpreport
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
	adb = analysis.cpa.analysisdatabase.CPAAnalysisDatabase(db)

	if True:
		start = time.clock()
		print "Code conditioning: Method Call"
		optimization.methodcall.methodCall(extractor, adb)
		print "Time: %.2e" % (time.clock()-start)

	start = time.clock()
	print "Analysis: Object Lifetime"
	la =  analysis.cpa.lifetimeanalysis.LifetimeAnalysis()
	la.process(dataflow)
	dataflow.db.lifetime = la # HACK
	print "Time: %.2e" % (time.clock()-start)

	if True:
		print "Code conditioning: Simplify"
		start = time.clock()
		live = db.liveFunctions()
		desc = extractor.desc

		for func in desc.functions:
			code = func.code
			if code not in descriptiveLUT and code in live:
				simplify(extractor, adb, code)
		print "Time: %.2e" % (time.clock()-start)

	if True:
		print "Code conditioning: Lower"
		start = time.clock()
		# Flatten the interpreter calls.
		# Needs to be done before cloning, as cloning can only
		# redirect direct calls.
		for func in adb.liveFunctions():
			if not func in descriptiveLUT:
				callConverter(extractor, adb, func)
		print "Time: %.2e" % (time.clock()-start)

	if True:
		start = time.clock()
		print "Code conditioning: Clone"
		clone(extractor, entryPoints, adb)
		print "Time: %.2e" % (time.clock()-start)

def cpaAnalyze(e, entryPoints):
	print "Analyize"
	start = time.clock()
	result = analysis.cpa.evaluate(e, entryPoints)
	elapsed = time.clock()-start
	print "Constraints:   %d" % len(result.constraints)
	print "Contexts:      %d" % len(result.liveContexts)
	print "Code:          %d" % len(result.liveCode)
	print "Contexts/Code: %.1f" % (len(result.liveContexts)/max(len(result.liveCode), 1))
	print "Slot Memory:   %.1f kB" % (result.slotMemory()/1024.0)

	print "Decompile:     %.3f s" % (result.decompileTime)
	print "Solve:         %.3f s" % (result.solveTime)
	print "Total:         %.3f s" % (elapsed)
	print

	return result

def cpaPass(e, entryPoints):
	result = cpaAnalyze(e, entryPoints)

	start = time.clock()
	codeConditioning(e, entryPoints, result)
	print "Optimize: %.3f" % (time.clock()-start)

	return result

def cpaDump(name, e, result, entryPoints):
	print "Dump..."
	start = time.clock()
	analysis.cpa.dumpreport.dump(name, e, result, entryPoints)
	print "Dump: %.3f" % (time.clock()-start)

def evaluate(name, e, entryPoints):
	cpaHeader(1)
	result = cpaPass(e, entryPoints)

	#analysis.shape.evaluate(e, entryPoints, result)

	if False:
		cpaHeader(2)
		result = cpaPass(e, entryPoints)

	cpaDump(name, e, result, entryPoints)
