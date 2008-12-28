import time
from programIR.python.program import Object

from decompiler.constantfinder import findCodeReferencedObjects


#
# Eliminates all unreferenced objects and code from a given program
#


def getLiveFunctions(prgm):
	liveFunctions 		= prgm.outputs['liveFunction'].enumerateSet()
	return liveFunctions


def getTypeSet(objs):
	ts = set()
	for obj in objs:
		ts.add(obj.type)
	return ts

def getLiveHeap(prgm):
	# Maintains the order
	liveHeap 		= prgm.outputs['liveHeap'].enumerateSet()

##	# HACK analysis doesn't read types, but the implementation need them.
##	delta = liveHeap
##	while delta:
##		newHeap = getTypeSet(delta)-liveHeap
##		liveHeap.update(newHeap)
##		delta = newHeap

	return liveHeap


def cullHeapReferences(desc, prgm, liveHeap):
	prevRef = 0
	currentRef = 0

	# Cull the internal pointer of the heap objects
	for obj in desc.objects:
		if isinstance(obj, Object):
			if obj.typeinfo and obj.typeinfo.abstractInstance != None and obj.typeinfo.abstractInstance not in liveHeap:
				obj.typeinfo.abstractInstance = None
			
			prevRef += len(obj.slot)
			prevRef += len(obj.array)
			prevRef += len(obj.dictionary)
			prevRef += len(obj.lowlevel)			

			objAllRead = prgm.outputs['readAnywhere'].restrict(h=obj)
			if objAllRead.maybeTrue():
				if obj.slot:
					objRead = objAllRead.restrict(t='Attribute')
					newdict = {}
					if objRead.maybeTrue():
						for k, v in obj.slot.iteritems():
							if objRead.restrict(fh=k).maybeTrue():
								newdict[k] = v
					obj.slot = newdict
					currentRef += len(newdict)


				if obj.array:
					objRead = objAllRead.restrict(t='Array')
					newdict = {}
					if objRead.maybeTrue():
						for k, v in obj.array.iteritems():
							if objRead.restrict(fh=k).maybeTrue():
								newdict[k] = v
					obj.array = newdict
					currentRef += len(newdict)


				if obj.dictionary:
					objRead = objAllRead.restrict(t='Dictionary')
					newdict= {}
					if objRead.maybeTrue():
						for k, v in obj.dictionary.iteritems():
							if objRead.restrict(fh=k).maybeTrue():
								newdict[k] = v
					obj.dictionary = newdict
					currentRef += len(newdict)

				if obj.lowlevel:
					objRead = objAllRead.restrict(t='LowLevel')
					
					newdict = {}
					if objRead.maybeTrue():
						for k, v in obj.lowlevel.iteritems():
							if objRead.restrict(fh=k).maybeTrue():
								newdict[k] = v
					obj.lowlevel = newdict
					currentRef += len(newdict)
			else:
				obj.slot = {}
				obj.array = {}
				obj.dictionary = {}
				obj.lowlevel = {}
			


	print "Refr: %d/%d = %.3f" % (currentRef, prevRef, float(currentRef)/prevRef)	

def cullProgram(desc, prgm, entryPoints, debug=False):
	start = time.clock()


	# Cull functions
	liveFunctions = getLiveFunctions(prgm)
	newFunctions = [func for func in desc.functions if func in liveFunctions]

	if debug:
		for func in desc.functions:
			if func not in liveFunctions:
				print "Kill", func.name
				
	print "Func: %d/%d = %.3f" % (len(newFunctions), len(desc.functions), float(len(newFunctions))/len(desc.functions))
	desc.functions = newFunctions

	# Cull heap objects
	# If GC technique is used, liveness depends on functions, so cull functions first.
	liveHeap = getLiveHeap(prgm)

	# All objects visible from the code are live.
	codeReferenced = findCodeReferencedObjects(desc.functions, entryPoints)
	liveHeap.update(codeReferenced)

	if debug:
		for obj in desc.objects:
			if obj not in liveHeap:
				print "Kill", obj

	
	newHeap = [obj for obj in desc.objects if obj in liveHeap]
	print "Heap: %d/%d = %.3f" % (len(newHeap), len(desc.objects), float(len(newHeap))/len(desc.objects))
	desc.objects   = newHeap


	cullHeapReferences(desc, prgm, liveHeap)
	

	# Cull the callLUT
	# TODO limit to the actual types called?
	newCallLUT = {}
	for obj, func in desc.callLUT.iteritems():
		if obj in liveHeap and func in liveFunctions:
			newCallLUT[obj] = func			
	desc.callLUT   = newCallLUT


	print "Cull: %.1fms" % ((time.clock()-start)*1000.0)
