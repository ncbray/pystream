from util.xmloutput  import XMLOutput
from common import simplecodegen

import os.path
from util import assureDirectoryExists

from programIR.python.ast import isPythonAST

import config

def makeReportDirectory(moduleName):
	reportdir = os.path.join(config.outputDirectory, moduleName)
	assureDirectoryExists(reportdir)
	return reportdir

def makeOutput(reportDir, filename):
	fullpath = os.path.join(reportDir, filename)
	fout = open(fullpath, 'w')
	out = XMLOutput(fout)
	scg = simplecodegen.SimpleCodeGen(out) # HACK?
	return out, scg

def functionShortName(out, func, funcMap=None):
	if isinstance(func, str):
		name = func
		args = ()
	elif isPythonAST(func):
		name = func.name
		args = func.code.parameternames
	else:
		assert hasattr(func, 'name'), repr(func)
		name = func.name
		args = [arg.name for arg in func.args]

	if funcMap != None and func in funcMap:
		out.begin('a', href=funcMap.get(func, 'error.html'))
	out << "%s(%s)" % (name, ", ".join(args))
	if funcMap != None and func in funcMap:
		out.end('a')


def heapShortName(out, heap, heapMap=None):
	if heapMap != None and heap in heapMap:
		out.begin('a', href=heapMap.get(heap, 'error.html'))
	out << repr(heap)
	if heapMap != None and heap in heapMap:
		out.end('a')

def dumpFunctionInfo(builder, prgm, func, funcMap, heapMap, out, scg):
	ast = func
	fn = func

	out.begin('h2')
	functionShortName(out, func)
	out.end('h2')
	
	if isPythonAST(ast):
		# Print the code
		out.begin('pre')
		scg.walk(ast)
		out.end('pre')
	
	nameLUT = scg.seg.localLUT

	recursive = prgm.outputs['recursiveFunction'].restrict(f=fn).maybeTrue()
	out << "Recursive: %s\n" % str(recursive)


	# Print the pointers
	out.begin('h3')
	out << 'varPoint'
	out.end('h3')
	out.begin('pre')

	lcls = prgm.inputs['containsVariable'].restrict(f=fn)

	def printLocal(var):
		out << '\t'+nameLUT.get(var, var.name)+'\n'

		def printVarPoint((h,)):
			#out << '\t\t'+str(c2)+'\n'
			out << '\t\t'
			heapShortName(out, h, heapMap)
			out.endl()

		rel = prgm.outputs['varPoint'].restrict(cv={'v':var}).forget('cv', 'ch.c')

		if rel.maybeTrue():
			rel.enumerate(printVarPoint)
		else:
			out << "\t\tNo information.\n"


	lcls.enumerate(printLocal)
	out.endl()
	out.end('pre')



	# Print the invocations
	out.begin('h3')
	out << 'Returns'
	out.end('h3')
	out.begin('pre')

	def printVarPoint(h):
		out << '\t'
		heapShortName(out, h, heapMap)
		out.endl()

	rel = prgm.outputs['funcReturns'].restrict(f=fn)

	if rel.maybeTrue():
		rel.enumerate(printVarPoint)
	else:
		out << "\tNo information.\n"
	out.endl()
	out.end('pre')




	### Read/modify/create ###

	out.begin('h3')
	out << 'read'
	out.end('h3')
	out.begin('pre')

	restrict = {'cf':{'f':fn}}
	reads = prgm.outputs['read'].restrict(**restrict).forget('cf')

	def printField(f):
		out << '\t\t'+str(f)+'\n'

	def printRead((h,)):
		#out << '\t'+str(c)+'\n'
		out << '\t'
		heapShortName(out, h, heapMap)
		out.endl()
		readF = reads.restrict(h={'h':h}).forget('h')
		readF.enumerate(printField)					 
		out.endl()

	readH = reads.forget('f', 'h.c')
	readH.enumerate(printRead)
	out.end('pre')

	out.begin('h3')
	out << 'modify'
	out.end('h3')
	out.begin('pre')


	restrict = {'cf':{'f':fn}}
	reads = prgm.outputs['modify'].restrict(**restrict).forget('cf')

	def printField(f):
		out << '\t\t'+str(f)+'\n'

	def printRead((h,)):
		#out << '\t'+str(c)+'\n'
		out << '\t'
		heapShortName(out, h, heapMap)
		out.endl()
		readF = reads.restrict(h={'h':h}).forget('h')
		readF.enumerate(printField)					 
		out.endl()

	readH = reads.forget('f', 'h.c')
	readH.enumerate(printRead)
	out.end('pre')

	out.begin('h3')
	out << 'create'
	out.end('h3')
	out.begin('pre')

	restrict = {'cf':{'f':fn}}
	reads = prgm.outputs['create'].restrict(**restrict).forget('cf', 'h.c')

	def printRead((h,)):
		#out << '\t\t'+str(c1)+'\n'
		#out << '\t'+str(c)+'\n'
		out << '\t'
		heapShortName(out, h, heapMap)
		out.endl()
	reads.enumerate(printRead)
	out.end('pre')
	


	### Errors ###
	# TODO figure out how to filter by function?
	bytecodes = prgm.inputs['containsBytecode'].restrict(f=fn)

	out.begin('h3')
	out << 'Invalid Calls'
	out.end('h3')
	out.begin('pre')

##	def printInvalid(o, h):
##		out << "\t"+str(o)+"\t"+str(h)+"\n"
	def printInvalid(h):
		out << "\t"+str(h)+"\n"


	def printBytecode(b):
		invalid = prgm.outputs['invalidOperation'].restrict(b=b)
		invalid.enumerate(printInvalid)


	out.begin('font', color="#FF0000")
	bytecodes.enumerate(printBytecode)
	out.end('font')
	out.end('pre')
	out.endl()

	## Invocation edges.

	# Print the invocations
	out.begin('h3')
	out << 'IE In'
	out.end('h3')
	out.begin('pre')

	def printVarPoint((b,)):
		out << '\tByte: '+str(b)+'\n'
		funcs = prgm.inputs['containsBytecode'].restrict(b=b)
		for f in funcs.enumerateSet():
			out << "\t\t"
			functionShortName(out, f, funcMap)
			out.endl()			
		out.endl()

	res = {'cf':{'f':fn}}
	rel = prgm.outputs['liveIE'].restrict(**res).forget('cf', 'cb.c')

	if rel.maybeTrue():
		rel.enumerate(printVarPoint)

	out.end('pre')
	out.endl() 

	# Print the invocations
	out.begin('h3')
	out << 'IE Out'
	out.end('h3')
	out.begin('pre')

	def printVarPoint((f,)):
		#out << '\t\tFrom: '+str(c1)+'\n'
		#out << '\t\tTo:   '+str(c2)+'\n'
		out << '\t\tFunc: '
		functionShortName(out, f, funcMap)
		out.endl()

	def invocationBytecode(bytecode):
		res = {'cb':{'b':bytecode}}
		rel = prgm.outputs['liveIE'].restrict(**res).forget('cb', 'cf.c')

		if rel.maybeTrue():
			out << '\t'+str(bytecode)+'\n'
			rel.enumerate(printVarPoint)


	bytecodes.enumerate(invocationBytecode)

	out.end('pre')
	out.endl()


def dumpHeapInfo(builder, prgm, heap, liveHeap, funcMap, heapMap, out):
	restriction = {'h1':{'h':heap}}
	con = prgm.outputs['heapPoint'].forget('f', 'h2').restrict(**restriction)

	desc = builder.extractor.desc
	
	if con.maybeTrue():

		contexts = con.enumerateList()

		out.begin('h3')
		heapShortName(out, heap)
		out.end('h3')

		if heap in desc.callLUT:
			out.begin('p')
			out << "Call: "
			functionShortName(out, desc.callLUT[heap], funcMap)
			out.end('p')


		concrete = prgm.outputs['concrete'].restrict(h=heap).maybeTrue()
		out << ("Concrete" if concrete else "Abstract") << "\n"
		
		out.begin('pre')

		#recursive = prgm.outputs['recursiveType'].restrict(h=heap).maybeTrue()
		#out << "Recursive: %s\n" % str(recursive)

		for (con,), in contexts:
			#esc = prgm.outputs['escape'].restrict(h=(con, o)).maybeTrue()	
			#out << '\t'+str(con)+' ' + str(esc) + '\n'

			out << '\t'+str(con)+ '\n'

			# Print fields
			restriction = {'h1':(con, heap)}
			points = prgm.outputs['heapPoint'].restrict(**restriction)
			fieldDB = points.forget('h2')
			fields = fieldDB.enumerateList()

			globalEscape = prgm.outputs['globalEscape'].restrict(**{'h':(con, heap)}).maybeTrue()
			out << "\t\t" << ("Global Escape" if globalEscape else "No Global Escape") << "\n\n"


			for field, in fields:
				fpoints = points.restrict(f=field)
				out << '\t\t'+str(field)+'\n'

				def printPair((c2, h)):
					out << '\t\t\t'+str(c2)+' / '
					heapShortName(out, h, heapMap)
					out.endl()

				fpoints.enumerate(printPair)

			out.endl()

			out << "\t\t"
			out.begin('b')
			out << 'Held By Function'
			out.end('b')
			out.endl()

			funcs = prgm.outputs['heldByFunction'].restrict(**{'h':(con, heap)}).forget('f.c')
			funcs = funcs.enumerateList()
			for (f,), in funcs:
				out << '\t\t'
				functionShortName(out, f, funcMap)
				out.endl()
				#out << '\t\t'+str(c)+' / '+str(f)+'\n'
				
			out.endl()

			out << "\t\t"
			out.begin('b')
			out << 'Held By Heap'
			out.end('b')
			out.endl()
			
			held = prgm.outputs['heapPoint'].restrict(**{'h2':(con, heap)}).forget('h1.c', 'f')
			held = held.enumerateList()
			for (h,), in held:
				if h in liveHeap:
					out << '\t\t'
					heapShortName(out, h, heapMap)
					out.endl()
			out.endl()
			
		out.endl()
		out.end('pre')	

def dumpHeader(out):
	out.begin('p')
	out << "["
	out.begin('a', href="index.html")
	out << "Index"
	out.end('a')
	out << "]"
	out.end('p')
	out.endl()

def getTypeSet(objs):
	ts = set()
	for obj in objs:
		ts.add(obj.type)
	return ts
	
def dumpReport(ce, prgm, moduleName):
	builder = ce
	
	reportDir = makeReportDirectory(moduleName)
	out, scg = makeOutput(reportDir, 'index.html')


	# Maintains the order.
	liveFunctions 		= prgm.outputs['liveFunction'].enumerateSet()
	filteredFunctions 	= [func for func in prgm.domains['function'] if func in liveFunctions]


	funcMap = {}
	for i, func in enumerate(filteredFunctions):
		funcMap[func] = "f%07d.html" % i


	# Maintains the order
	liveHeap 		= prgm.outputs['liveHeap'].enumerateSet()

	# HACK analysis doesn't read types, but the implementation need them.
	delta = liveHeap
	while delta:
		newHeap = getTypeSet(delta)-liveHeap
		liveHeap.update(newHeap)
		delta = newHeap
	
	filteredHeap 		= [func for func in prgm.domains['heap'] if func in liveHeap] 


	heapMap = {}
	for i, heap in enumerate(filteredHeap):
		heapMap[heap] = "h%07d.html" % i


	out.begin('h2')
	out << "Function Index"
	out.end('h2')
	

	out.begin('ul')
	for func in filteredFunctions:
		out.begin('li')
		functionShortName(out, func, funcMap)
		out.end('li')
	out.end('ul')
	out.endl() 	


	out.begin('h2')
	out << "Heap Index"
	out.end('h2')


	out.begin('ul')
	for heap in filteredHeap:
		out.begin('li')
		out.begin('a', href=heapMap[heap])
		out << heap
		out.end('a')
		out.end('li')
	out.end('ul')
	out.endl() 	



	### Errors ###
	invalid = prgm.outputs['invalidOperation']

	if invalid.maybeTrue():
		out.begin('h3')
		out << 'Invalid Calls'
		out.end('h3')
		out.begin('pre')


		def printInvalid(b, h):
			f = prgm.inputs['containsBytecode'].restrict(b=b)
			f = tuple(f.enumerateSet())[0] # HACK

			out << '\t'
			functionShortName(out, f, funcMap)
			out << " -> "
			heapShortName(out, h, heapMap)
			out.endl()



		out.begin('font', color="#FF0000")
		invalid.enumerate(printInvalid)
		out.end('font')
		out.end('pre')
		out.endl()


	for func in filteredFunctions:
		out, scg = makeOutput(reportDir, funcMap[func])
		dumpHeader(out)
		dumpFunctionInfo(ce, prgm, func, funcMap, heapMap, out, scg)
		out.endl() 	


	for heap in filteredHeap:
		out, scg = makeOutput(reportDir, heapMap[heap])
		dumpHeader(out)
		dumpHeapInfo(ce, prgm, heap, liveHeap, funcMap, heapMap, out)
		out.endl() 	



	out.close()
