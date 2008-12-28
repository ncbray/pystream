from __future__ import absolute_import

class FIAnalyze(object):
	def domains():
		heap()		# An object in memory.
		variable()	# A slot on the stack.

		bytecode()	# A unique name for a single operation.

		function()	# More correctly "executable code," rather than a function object.

		parameter() 	# An integer representing the parameter position.
		fieldtype() 	# slot, array index, dictionary index, primitive

		functionSignature()
		#callSignature()

	def structures():
		# 2 CFA
		#callpath(('b1',bytecode), ('b2',bytecode))

		# 3 CFA
		callpath(('b1',bytecode), ('b2',bytecode), ('b3',bytecode))

		# Context sensitive versions of varrious types.
		variableC(('c',callpath), ('v', variable))
		heapC(('c',callpath), ('h', heap))
		bytecodeC(('c',callpath), ('b', bytecode))
		functionC(('c',callpath), ('f', function))

		field(('t',fieldtype), ('h',heap))

	def inputRelations():
		varPoint0(('v',variable), ('ch',heapC))
		
		heapPoint0(('h1',heapC), ('f',field), ('h2',heapC))
		
		reachable0(('cf', functionC))
		IE0(('cb',bytecodeC), ('cf',functionC))

		# Should we change the context at this call site?
		# Calls within the object model don't change the context.
		advanceContext(('b', bytecode))

		# Currently just an "assign" constraint
		merge(('v1',variable), ('v2',variable))

		# Information about functions.
		containsBytecode(('f',function), ('b',bytecode))
		containsVariable(('f',function), ('v',variable))

		selfParam(('f',function), ('v',variable)) # Low level "self", not visible as an argument.
		formalParam(('f',function), ('z',parameter), ('v',variable))
		returns(('f',function), ('z',parameter), ('v',variable))


		### Bytecode layer ###

		# An object model operation.
		# For a given operation on a given object, what function should be called?


		# Indirect calls
		call(('b',bytecode), ('v',variable))
		callLUT(('h', heap), ('f', function))

		# Direct calls
		directCall(('b',bytecode), ('f', function))

		# Parameter passing and return values for object mode operations.
		opResult(('v',variable), ('z',parameter), ('b',bytecode))
		actualParam(('b',bytecode), ('z',parameter), ('v',variable))

		### Low-level layer ###
		allocateOp(('b', bytecode), ('v',variable))
		typeOp(('b', bytecode), ('v',variable))


		# load/store given a variable field.
		load(('b',bytecode), ('expr',variable), ('ft',fieldtype), ('f',variable))
		store(('b',bytecode), ('expr',variable), ('ft',fieldtype), ('f',variable), ('value',variable))


		# TODO implement as maps?
		instanceOf(('t', heap), ('h', heap))


	def internalRelations():
		liveBytecode(('cb', bytecodeC))
		nextContextC(('cb', bytecodeC), ('c', callpath))
		assign(('dest',variableC), ('source',variableC))
		IE(('cb',bytecodeC), ('cf',functionC))


	def outputRelations():
		# Is it a unique object?
		concrete(('h', heap))

		liveIE(('cb',bytecodeC), ('cf',functionC))

		varPoint(('cv',variableC), ('ch',heapC))
		heapPoint(('h1',heapC), ('f',field), ('h2',heapC))

		funcReturns(('f',function), ('h', heap))

		functionCalls(('f1',functionC), ('f2',functionC))
		recursiveFunction(('f',function))
		
		liveFunctionC(('f', functionC))
		liveFunction(('f', function))
		
		liveHeap(('h', heap))


		read(('cf', functionC), ('h', heapC), ('f',field))
		modify(('cf', functionC), ('h', heapC), ('f',field))
		create(('cf', functionC), ('h', heapC))

		readAnywhere(('h', heap), ('t', fieldtype), ('fh', heap))
		modifyAnywhere(('h', heap), ('t', fieldtype), ('fh', heap))

		invalidOperation(('b',bytecode), ('h', heap))

		heldByFunction(('h',heapC), ('f',functionC))

		globalEscape(('h',heapC))


	def expressions():
		############################
		### Context manipulation ###
		############################

		# CFA 2
##		nextContextC(((_, bl0a), ba), (bl0b, bb)) <= advanceContext(ba) \
##				  & (bl0a==bl0b) & (ba==bb)

		# CFA 3
		nextContextC(((_, b1a, b0a), ba), (b1b, b0b, bb)) <= advanceContext(ba) \
				  & (b1a==b1b) & (b0a==b0b) & (ba==bb)

		# Valid for k-CFA
		# TODO allow identical symbols on the left side. (Eliminates explicit equality.)
		nextContextC((c1, b), c2) <= ~advanceContext(b) & (c1==c2)


		############################
		### Inital program state ###
		############################
		# Copied from inputs, as inputs are immutable.

		concrete(h) <= ~instanceOf(_, h)
		
		# HACK Used for loading constants.
		# TODO model contant loading as an explicit operation?
		varPoint((_, v), ch) <= varPoint0(v, ch)

		# Heap and global pointers.
		heapPoint(ch1, f, ch2) <= heapPoint0(ch1, f, ch2)

		# Entry point.
		IE(cb, cf) <= IE0(cb, cf)

		# Convert merges into an assignment.
		# Gating by live bytecode is not sound, as a function may have no bytecodes...
		assign((c1, v1), (c2, v2)) <= merge(v1, v2) & (c1==c2)


		######################
		### Basic Analysis ###
		######################

		# Only allow reachable functions to affect the analysis
		liveBytecode((c, b)) <= reachable0((c, f)) & containsBytecode(f, b)
		liveBytecode((c2, b2)) <= liveBytecode(cb) & IE(cb, (c2, f2)) & containsBytecode(f2, b2)

		# Assignments
		# v1 = v2
		varPoint(cv1, ch) <= assign(cv1, cv2)&varPoint(cv2, ch)


		#############
		### Calls ###
		#############

		# Calls naturally cross contexts.
		# As such, the call rules explicitly expand context-sensitive structures
		# and rearange the contexts.
		
		# Operation invocation
		# Converts at object model call into a code invocation.
		IE((cb, b), (cf, func)) <= liveBytecode((cb, b)) & call(b, v) & varPoint((cb, v),( _, h)) \
		       & callLUT(h, func) & nextContextC((cb, b), cf)


		# Direct call
		# Used for calling known code directly.
		IE((cb, b), (cf, func)) <= liveBytecode((cb, b)) & directCall(b, func) & nextContextC((cb, b), cf)
		#IE((cb, b), (cf, func)) <= directCall(b, func) & nextContextC((cb, b), cf)

		# Pass self parameter
		# This is the argument that the object model call was invoked on.
		# TODO closure parameter.
		assign((cf, v2), (cb, v1)) <= IE((cb, b), (cf, f)) & call(b, v1) & selfParam(f, v2)

		# Pass arguments
		assign((cf, v2), (cb, v1)) <= IE((cb, b), (cf, f)) & formalParam(f, z, v2) & actualParam(b, z, v1)

		# Pass back returns
		# A little hackish, as it allows functions to return multiple values.
		# Multiple values are only returned from sequence unpacking opertions.
		assign((cb, v1), (cf, v2)) <= opResult(v1, z, b) & IE((cb, b), (cf, f)) & returns(f, z, v2)


		# Does this closure speed anything up?
		#assign(v1, v3) <= assign(v1, v2) & assign(v2, v3)

		############################
		### Low-level operations ###
		############################

		# Load object attribute/list index/dictionary item
		varPoint((ce, vr), ch2) <= opResult(vr, _, b) & load(b, ve, t, vf) \
			      & varPoint((ce, ve), che) \
			      & varPoint((ce, vf), (_, hf)) \
			      & heapPoint(che, (t, hf), ch2)


		# Store attribute - must be gated by liveness to prevent polution.
		heapPoint(chexpr, (t, hf), chval) <= liveBytecode((c, b)) & store(b, expr, t, f, val) \
			      & varPoint((c, expr), chexpr) \
			      & varPoint((c, f), (_, hf)) \
			      & varPoint((c, val), chval)

		###########################################
		### Context-sensitive object allocation ###
		###########################################

		# Allocate a new object.
		varPoint((c1, v1), (c2, inst)) <= opResult(v1, _, b) & allocateOp(b, temp) & liveBytecode((c1, b))\
			     & varPoint((c1, temp), (_, cls)) & instanceOf(cls, inst) & (c1==c2)


		###############
		### REPORTS ###
		###############

		liveIE(b, f) <= liveBytecode(b) & IE(b, f)

		# A function may have no bytecodes, so function liveness is defined
		# by a live bytecode calling a given function.
		liveFunctionC(f) <= liveIE(_, f)
		liveFunction(f) <= liveFunctionC((_, f))

		# Report Function Return Types
		funcReturns(f, h) <= returns(f, _, v) & varPoint((_, v), (_, h))

		# Report Call Recursion
		functionCalls((c, f), f2) <= containsBytecode(f, b) & liveIE((c, b), f2)
		functionCalls(f1, f3) <= functionCalls(f1, f2) & functionCalls(f2, f3)
	
		recursiveFunction(f) <= functionCalls((c, f), (c, f))	


		# Did we invoke an unsupported operation?
		invalidOperation(b, h) <= liveBytecode((cb, b)) & call(b, v) & \
				    varPoint((cb, v),( _, h)) & ~callLUT(h, _) 



		# Information for region/escape analysis
##		globalEscape((c2, h2)) <= heapPoint((_, h1), _, (c2, h2)) & concrete(h1) & ~concrete(h2)
##		globalEscape((c2, h2)) <= heapPoint(h1, _, (c2, h2)) & globalEscape(h1) & ~concrete(h2)

		globalEscape((_, h2)) <= concrete(h2)
		globalEscape(h2) <= globalEscape(h1) & heapPoint(h1, _, h2)

		# heldByFunction(h, f) implies there is a path from a local of f to h
		heldByFunction((ch, h), (cf, f)) <= liveFunctionC((cf, f)) & containsVariable(f, v) & varPoint((cf, v), (ch, h)) & ~concrete(h)
		heldByFunction((c, h1), f) <= heldByFunction(h2, f) & heapPoint(h2, _, (c, h1)) & ~concrete(h1)




		# Report Heap Read
		read((c, func), che, (t, hf)) <= liveBytecode((c, b)) & containsBytecode(func, b) \
			      & load(b, ve, t, vf) \
			      & varPoint((c, ve), che) \
			      & varPoint((c, vf), (_, hf))

		# Propigate backwards
		read((c, func), ch, f) <= containsBytecode(func, b) & liveIE((c, b), func2) & read(func2, ch, f)



		# Report Heap Modify
		modify((c, func), che, (t, hf)) <= liveBytecode((c, b)) & containsBytecode(func, b) \
			      & store(b, ve, t, vf, vs) \
			      & varPoint((c, ve), che) \
			      & varPoint((c, vf), (_, hf)) \
			      & varPoint((c, vs), _) # Filter out unused writes.

		# Propigate backwards
		modify((c, func), ch, f) <= containsBytecode(func, b) & liveIE((c, b), func2) & modify(func2, ch, f)



		# Report object creation
		# If it escapes globally, don't propigate it.
		create((c1, func), (c2, inst)) <= liveBytecode((c1, b)) & allocateOp(b, temp) & containsBytecode(func, b)\
			     & varPoint((c1, temp), (_, cls)) & instanceOf(cls, inst) & (c1==c2) 
		# HACK DISABLE & ~globalEscape((c2, inst))


		# Propagate backwards
		create((c, func), ch) <= containsBytecode(func, b) & liveIE((c, b), func2) & create(func2, ch) & heldByFunction(ch, (c, func))
		#create((c, func), ch) <= containsBytecode(func, b) & liveIE((c, b), func2) & create(func2, ch) & globalEscape(ch)


		# Globally summarize read and modify.
		# Mainly used to simplifying pre-existing structures, so context sensitivity is not needed
		readAnywhere(h, t, fn)   <= read(_, (_, h), (t, fn))
		modifyAnywhere(h, t, fn) <= modify(_, (_, h), (t, fn))


		# Any heap name that an operation is performed on is "live"
		liveHeap(h) <= liveBytecode((cb, b)) & call(b, v) & varPoint((cb, v),( _, h))

		liveHeap(h) <= readAnywhere(_, _, h)
		liveHeap(h) <= modifyAnywhere(_, _, h)
		liveHeap(h) <= readAnywhere(h, _, _)
		liveHeap(h) <= modifyAnywhere(h, _, _)
		liveHeap(h) <= read(_, (_, h1), f) & heapPoint((_, h1), f, (_, h))
