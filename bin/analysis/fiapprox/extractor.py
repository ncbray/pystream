from __future__ import absolute_import

import random
import copy

import collections

from . dumpreport import dumpReport

#from analysis.bdddatalog.relational.managerhack import m

from . learnorder import runTrials

from . signatures import gatherSignatures

from programIR.python.ast import isPythonAST
from programIR.python.program import AbstractObject, Object

from util import xtypes


from . constraintextractor import NewConstraintExtractor

from . codeextractor import CodeExtractor
from analysis.fiapprox.llcodeextractor import LLCodeExtractor

# HACK
from stubs.stubcollector import exports


from . oplut import opLUT

import cProfile

from cStringIO import StringIO
from common.simplecodegen import SimpleCodeGen

from decompiler.constantfinder import findCodeReferencedObjects

def nextContext(previous, bytecode):
	return tuple(previous[1:])+(bytecode,)

def pack(*args):
	return tuple(args)


	
def addEntryPoint(ce, rootContext, fobj, argobjs):
	name = fobj.pyobj.func_name	
	ast = ce.extractor.desc.callLUT[fobj]

	# Create a "calling point" for each entry point being analyized.
	argnames = [obj.type.pyobj.__name__ for obj in argobjs]
	point = "_".join(pack('entry', name, *argnames))
	ce.addSymbol('bytecode', point)
	ce.addTuple('containsBytecode', 'rootfunc', point)
	ce.setArgs(point, argobjs)

	# Create an invocation edge.
	pointC = nextContext(rootContext, point)
	ce.addTuple('IE0', (rootContext, point), (pointC, ast))


def makeDirectReference(ce, obj):
	assert obj is not None
	if not ce.containsSymbol('variable', obj):
		ce.addSymbol('variable', obj)
		ce.addTuple('varPoint0', obj, (ce.rootContext, obj))

def makeHeapObjects(ce, objects, codeReferenced):
	# Create symbols for the pre-existing objects.
	for obj in objects:
		# Create a unique name for the heap object.
		ce.addSymbol('heap', obj)


	# Add simple predicates that require heap symbols.
	for obj in objects:
		# TODO only create for variables with explicit code references?
		# Also need pointers for functions, to get global variables?
		#if obj.isConcrete():
		# Create a dummy variable that point to the heap object.
		if obj in codeReferenced:
			makeDirectReference(ce, obj)

		# There may be no abstract instance, especially if the mmory image has been culled.
		if obj.isType() and obj.typeinfo.abstractInstance != None:
			ce.addTuple('instanceOf', obj, obj.typeinfo.abstractInstance)



def makeHeapPointers(ce, objects):
	### Create pointers between the pre-existing objects ###
	
	for src in objects:
		if src.isConcrete():
			csrc = (ce.rootContext, src)
			
			# HACK
			if isinstance(src, Object):
				# Slots
				for name, dst in src.slot.iteritems():
					field = ce.makeSlot(name)
					ce.addTuple('heapPoint0', csrc, field, (ce.rootContext, dst))

				# Array items
				for name, dst in src.array.iteritems():
					field = ce.makeIndex(name)
					ce.addTuple('heapPoint0', csrc, field, (ce.rootContext, dst))

				# Dictionary Items
				for name, dst in src.dictionary.iteritems():
					field = ce.makeKey(name)
					ce.addTuple('heapPoint0', csrc, field, (ce.rootContext, dst))

				for name, dst in src.lowlevel.iteritems():
					# HACK should remove "getObject"?
					field = ce.makeLowLevel(name) 
					ce.addTuple('heapPoint0', csrc, field, (ce.rootContext, dst))


def attachLLOperators(ce, obj):
	if obj in ce.extractor.desc.callLUT:
		ce.addTuple('callLUT', obj, ce.extractor.desc.callLUT[obj])
	
##	if '__get__' not in obj.type.typeinfo.all:
##		# Getter doesn't actually exist, create a passthrough getter
##		# TODO modify memory image and test?
##		fobj = ce.extractor.getObject(exports['default__get__'])
##		ast = ce.extractor.desc.callLUT[fobj]
##		ce.attachOperator('GetProperty', obj, ast)

# Builds the feature database.
def attachOperators(ce, objects):
	# Attach operations to each object.
	for src in objects:
		attachLLOperators(ce, src)

def checkFunctionObject(ce, obj):
		assert ce.extractor.contains(obj.pyobj), obj
		assert ce.extractor.complete[obj], obj
		
		if not ce.extractor.contains(obj.pyobj.func_globals):
			print obj
			print obj.slot
			print obj.array
			print obj.dictionary
			print
			print obj.type

			print obj.type.slot
			print obj.type.array
			print obj.type.dictionary

		assert ce.extractor.contains(obj.pyobj.func_globals), obj

def extractFunctions(ce, functions):
	extracted = set()

	# Some functions may call others directly, so create all the names first.
	for ast in functions:
		assert not ast in extracted, ast
		ce.addSymbol('function', ast)
		extracted.add(ast)

	# Build a function ast -> function object index.  Used for determining the global dictionary.
	funcToObj = {}
	for obj, func in ce.extractor.desc.callLUT.iteritems():
		if isinstance(obj, Object) and isinstance(obj.pyobj, xtypes.FunctionType):
			assert not func in funcToObj
			funcToObj[func] = obj

	# Extract the code.
	for ast in functions:
		if isPythonAST(ast):
			obj = funcToObj.get(ast)
			makeDirectReference(ce, obj)
			try:
				CodeExtractor(ce, obj, ast, ce.rootContext).walk(ast)
			except:
				print
				print "#######################################"
				print "Function generated an internal error..."
				print "#######################################"
				sio = StringIO()
				scg = SimpleCodeGen(sio)
				scg.walk(ast)
				print sio.getvalue()
				raise
				raise
		else:
			LLCodeExtractor(ce).walk(ast)


def buildFeatureDatabase(extractor, entryPoints):
	objects   = extractor.desc.objects
	functions = extractor.desc.functions
	
	codeReferenced = findCodeReferencedObjects(functions, entryPoints)

	objectSet = set(objects)

	for refed in codeReferenced:
		if not refed in objectSet:
			for obj in objectSet:
				if isinstance(obj, Object) and isinstance(obj.pyobj, type(refed.pyobj)):
					if obj.pyobj is refed.pyobj:
						print "#"*60
						print "!", id(obj), id(obj.pyobj), obj
						print "#"*60
			
			assert False, (id(refed), id(refed.pyobj), refed)

	
	cfaLevel 	= 3
	rootContext 	= tuple(['root']*cfaLevel)
	
	ce = NewConstraintExtractor(extractor, rootContext)

	# Create the root context
	ce.addSymbol('bytecode', 'root')
	ce.addSymbol('function', 'rootfunc')
	ce.addTuple('reachable0', (rootContext, 'rootfunc'))

	# HACK for development, used for undefined direct calls.
	ce.addSymbol('function', 'null')

	makeHeapObjects(ce, objects, codeReferenced)

	### Initalize the functions ###
	# Needs constants to have assosiated variables.
	# As such, it is done after varPoint0 is created for heap objects.
	extractFunctions(ce, functions)

	### The interdependancies of the heap objects ###
	makeHeapPointers(ce, objects)
	attachOperators(ce, objects)

	### Initalize entry points ###
	for func, args in entryPoints:
		addEntryPoint(ce, rootContext, func, args)

	return ce

from optimization.cullprogram import cullProgram
from optimization.simplify import simplify


def firstAnalysisPass(moduleName, extractor, entryPoints, debugCull=False):	
	# moduleName: string, name of the library
	# entryPoints: list of (function object, list arg objects)


	extractor.finalize()
	extractor.desc.clusterObjects()
	
	gatherSignatures(extractor.desc)
	
	ce = buildFeatureDatabase(extractor, entryPoints)
	extractor.unfinalize()


	########################
	### Run the Analysis ###
	########################

	#best = ('globalVar', 'optype', 'parameter', 'bytecode', 'function', 'variable', 'heap', 'field', 'fieldtype')
	#best = ('globalVar', 'parameter', 'bytecode', 'function', 'variable', 'heap', 'field', 'fieldtype')
	#best = ('globalVar', 'parameter', 'bytecode', 'function', 'variable', 'heap', 'fieldtype')
	best = ('parameter', 'bytecode', 'function', 'variable', 'heap', 'fieldtype')
	
	if False:
		runTrials(ce, best)
	else:
		run(moduleName, ce, best)

	desc = ce.extractor.desc
	prgm = ce.prgm
	
	cullProgram(ce.extractor.desc, ce.prgm, entryPoints, debugCull)

	
	newfuncs = [simplify(extractor, prgm, func) for func in desc.functions]
	desc.functions = newfuncs

	return ce



def evaluate(moduleName, extractor, entryPoints, dump=False, debugCull=False):
	ce = firstAnalysisPass(moduleName, extractor, entryPoints, debugCull)
	if dump: dumpReport(ce, ce.prgm, moduleName)


def run(moduleName, ce, best):
	# Directed sampling.
	domains = best

	print "Compiling program."
	prgm = ce.makeInterpreter(domains)
	#prgm.interp.verbose = True

	print "Executing program."
	time = prgm.execute()

	print "FI time %s: %.1fms" % (moduleName, time*1000.0)
