from __future__ import absolute_import

import collections

from language.python.ast import *
import common.ssa as ssa

from util.visitor import StandardVisitor

from .. import errors
from . import pythonstack
from .. import flowblocks
from . import instructiontranslator

from language.python.annotations import codeOrigin

from common.errors import TemporaryLimitation

PythonStack = pythonstack.PythonStack

def appendSuite(current, next):
	# Only append if the next value is worthwhile
	if next and next.significant():
		if not current or not current.significant():
			# First block
			if not isinstance(next, Suite):
				next = Suite([next])
			current = next
		elif not isinstance(current, Suite):
			# Second block
			current = Suite([current, next])
		else:
			# All subsequent blocks
			current.append(next)
	return current


class DestackVisitor(StandardVisitor):
	def __init__(self, code, mname, extractor, callback, trace=False):
		StandardVisitor.__init__(self)
		self.ssa = ssa.SSADefinitions()
		self.code = code
		self.moduleName = mname
		self.locals = {}
		self.defns = collections.defaultdict(dict)
		self.extractor = extractor
		self.callback = callback
		self.trace = trace

	def getDefns(self, block):
		if block in self.defns:
			return self.defns[block]
		elif isinstance(block, Suite):
			assert block.blocks
			return self.getDefns(block.blocks[0])
		else:
			return {}

	def visitReturn(self, block, stack):
		assert isinstance(stack, PythonStack)
		assert stack.size() >= 1

		arg = stack.pop()
		defn = self.ssa.definition(arg)

		# Special case: returning None
		if isinstance(defn, Existing) and defn.object.isConstant() and defn.object.pyobj == None:
			arg = defn

		outblock = Return([arg])
		return outblock, None

	def visitRaise(self, block, stack):
		assert isinstance(stack, PythonStack)
		assert block.nargs <= stack.size()

		exception = None
		parameter = None
		traceback = None

		# The order is revered compared to the exception handlers? (!)
		if block.nargs >= 3:
			traceback = stack.pop()
		if block.nargs >= 2:
			parameter = stack.pop()
		if block.nargs >= 1:
			exception = stack.pop()

		outblock = Raise(exception, parameter, traceback)

		return outblock, None

	def visitBreak(self, block, stack):
		assert isinstance(stack, PythonStack)
		outblock = Break()
		return outblock, None

	def visitContinue(self, block, stack):
		assert isinstance(stack, PythonStack)
		outblock = Continue()
		return outblock, None


	def visitNormalExit(self, block, stack):
		assert isinstance(stack, PythonStack)
		return None, stack

	def visitNormalEntry(self, block, stack):
		assert isinstance(stack, PythonStack)
		return None, stack


	def visitLinear(self, block, stack):
		assert isinstance(stack, PythonStack), stack

		# Insurance, but probabally unessisary
		stack = stack.duplicate()

		t = instructiontranslator.InstructionTranslator(self.code, self.moduleName, self.ssa, self.locals, self.extractor, self.callback, self.trace)
		inst, defn, stack = t.translate(block.instructions, stack)

		outblock = Suite(inst)

		self.defns[outblock] = defn

		return outblock, stack

	def visitSuiteRegion(self, block, stack):
		assert isinstance(stack, PythonStack), stack
		return self.handleLinearRegion(block, stack)

	def visitMerge(self, block, stack):
		assert isinstance(stack, PythonStack), stack
		assert len(block.incoming) == 1 and block.numEntries()==1, block.incoming
		return None, stack

	def handleLinearRegion(self, region, stack):
		assert isinstance(stack, PythonStack), stack

		block = region.entry()

		output = None

		newdefns = {}

		while block:
			outblock, stack = self.visit(block, stack)

			if outblock != None and outblock in self.defns:
				for k, v in self.defns[outblock].iteritems():
					assert not k in newdefns, (k, newdefns)
					newdefns[k] = v

			assert isinstance(stack, PythonStack) or stack==None, block

			output = appendSuite(output, outblock)

			assert block.numExits() <= 1

			if block.numExits() == 0:
				# Stack exists if this is a normal exit
				break
			elif stack == None:
				break
			else:
				#assert stack != None or not block.next, (block, region, output)
				block = block.next

		self.defns[output] = newdefns

		return output, stack

	def getTOS(self, block, stack):
		assert block.origin, block
		lcl = stack.peek()
		conditional = ConvertToBool(lcl)
		conditional.rewriteAnnotation(origin=block.origin)

		defn = self.ssa.definition(lcl)

		maybeTrue = True
		maybeFalse = True


		if isinstance(defn, Existing) and defn.object.isConstant():
			# TODO wrap with exception handling mechanism
			b = bool(defn.object.pyobj)
			maybeTrue = b
			maybeFalse = not b

		return conditional, stack, (maybeTrue, maybeFalse)

	def handleCond(self, cond, stack):
		assert isinstance(stack, PythonStack), stack

		if isinstance(cond, flowblocks.Linear):
			block, stack = self.visit(cond, stack)
			conditional, framset, (maybeTrue, maybeFalse) = self.getTOS(cond, stack)

			temp = Local()
			assert isinstance(conditional, Expression), conditional
			assign = Assign(conditional, [temp])
			block.append(assign)
			condition = Condition(block, temp)
			#condition = Condition(block, conditional)
			tstack = stack.duplicate()
			fstack = stack.duplicate()
		else:
			condition, tstack, fstack, (maybeTrue, maybeFalse) = self.visit(cond, stack)

		assert isinstance(condition, Condition), condition

		return condition, tstack, fstack, (maybeTrue, maybeFalse)

	def visitCheckStack(self, block, stack):
		conditional, framset, (maybeTrue, maybeFalse) = self.getTOS(block, stack)
		assert isinstance(conditional, Expression), conditional

		temp = Local()
		assign = Assign(conditional, [temp])
		block = Suite([assign])
		condition = Condition(block, temp)

		#condition = Condition(Suite(), conditional)
		tstack = stack.duplicate()
		fstack = stack.duplicate()
		return condition, tstack, fstack, (maybeTrue, maybeFalse)

	def visitShortCircutOr(self, block, stack):
		assert isinstance(stack, PythonStack), stack

		terms = []
		stacks = []

		def accumulate(condition, stack):
			# TODO assert no abnormal exits?
			assert isinstance(stack, PythonStack), stack
			terms.append(condition)
			stacks.append(stack)

		maybeTrue = False
		maybeFalse = True

		fstack = stack
		for term in block.terms:
			condition, tstack, fstack, (termMaybeTrue, termMaybeFalse) = self.handleCond(term, fstack)
			accumulate(condition, tstack)

			maybeTrue |= termMaybeTrue
			if not termMaybeFalse:
				maybeFalse = False
				break

		#tstack = pythonstack.mergeStacks(stacks, [term.onExit for term in terms])
		# HACK
		tstack = pythonstack.mergeStacks(stacks, [[] for term in terms])


		if len(terms) == 1:
			return terms[0], tstack, fstack, (maybeTrue, maybeFalse)


		condition = ShortCircutOr(terms)

		# Convert into a condition.
		lcl = Local()
		temp = Local()

		preamble = Suite([])
		preamble.append(Assign(condition, [lcl]))
		conv = ConvertToBool(lcl)
		conv.rewriteAnnotation(origin=block.origin)
		preamble.append(Assign(conv, [temp]))
		condition = Condition(preamble, temp)

		return condition, tstack, fstack, (maybeTrue, maybeFalse)


	def visitShortCircutAnd(self, block, stack):
		assert isinstance(stack, PythonStack), stack

		terms = []
		stacks = []

		def accumulate(condition, stack):
			# TODO assert no abnormal exits?
			assert isinstance(stack, PythonStack), stack
			terms.append(condition)
			stacks.append(stack)

		maybeTrue = True
		maybeFalse = False


		tstack = stack
		for term in block.terms:
			condition, tstack, fstack, (termMaybeTrue, termMaybeFalse) = self.handleCond(term, tstack)
			accumulate(condition, fstack)

			maybeFalse |= termMaybeFalse
			if not termMaybeTrue:
				maybeTrue = False
				break

		#fstack = pythonstack.mergeStacks(stacks, [term.onExit for term in terms])
		# HACK
		fstack = pythonstack.mergeStacks(stacks, [[] for term in terms])

		if len(terms) == 1:
			return terms[0], tstack, fstack, (maybeTrue, maybeFalse)

		condition = ShortCircutAnd(terms)

		# Convert into a condition.
		lcl = Local()
		asgn1 = Assign(condition, [lcl])
		temp = Local()

		conv = ConvertToBool(lcl)
		conv.rewriteAnnotation(origin=block.origin)
		asgn2 = Assign(conv, [temp])
		condition = Condition(Suite([asgn1, asgn2]), temp)

		return condition, tstack, fstack, (maybeTrue, maybeFalse)

	# Entry point for processing conditionals
	def processCond(self, cond, stack):
		assert isinstance(stack, PythonStack), stack

		condition, tstack, fstack, (maybeTrue, maybeFalse) = self.handleCond(cond, stack)

		# TODO convert short circut into a normal conditional?

		return condition, tstack, fstack, (maybeTrue, maybeFalse)

	def handleBranch(self, block, stack):
		assert isinstance(stack, PythonStack), stack
		assert stack.size() >=1

		o = None

		if block:
			o, stack = self.visit(block, stack)
		else:
			o = Suite()

		return o, stack


	def visitSwitchRegion(self, block, stack):
		assert isinstance(stack, PythonStack), stack
		assert stack.size() >=1

		condition, tstack, fstack, (maybeTrue, maybeFalse) = self.processCond(block.cond, stack)

		assert maybeTrue or maybeFalse


		# TODO what to do if the condition is a short circut?
		assert isinstance(condition, Condition)
		if not maybeFalse:
			outblock, stack = self.handleBranch(block.t, tstack)
			#outblock = Suite([condition.preamble, Discard(condition.conditional), outblock])
			outblock = Suite([condition.preamble, outblock])

			return outblock, stack
		elif not maybeTrue:
			outblock, stack = self.handleBranch(block.f, fstack)
			#outblock = Suite([condition.preamble, Discard(condition.conditional), outblock])
			outblock = Suite([condition.preamble, outblock])
			return outblock, stack


		t, tstack = self.handleBranch(block.t, tstack)
		f, fstack = self.handleBranch(block.f, fstack)

		if tstack == None:
			stack = fstack
		elif fstack == None:
			stack = tstack
		elif not (tstack == fstack):
			raise TemporaryLimitation, "Cannot handle stack-carried merges."
			stack = pythonstack.mergeStacks((tstack, fstack), (t.onExit, f.onExit))
		else:
			stack = tstack

		# HACK why would this occur?
		if not t: t = Suite()
		if not f: f = Suite()

		outblock = Switch(condition, t, f)

		return outblock, stack


	def visitLoopElse(self, block, stack):
		assert isinstance(stack, PythonStack), stack


		suite, loopstack = self.visit(block.loop, stack.duplicate())

		# HACK for "for" loops"
		# We need a handle on the actual loop so we can
		#	1) attach the "else"
		#	2) attach the exit merges
		if isinstance(suite, Suite):
			# There may be multiple "loops"
			# if list comprehensions are used while creating the iterator.
			loop = None
			for child in reversed(suite.blocks):
				if isinstance(child, Loop):
					loop = child
					break
			assert loop, suite
		else:
			# This should no longer occur?
			loop = suite

		assert isinstance(loop, Loop), [suite, type(loop)]

		assert loopstack == None or loopstack == stack

		### Evaluate the loop "else" ###
		if block._else:
			else_, elsestack = self.visit(block._else, stack.duplicate())

			if else_ and not isinstance(else_, Suite):
				else_ = Suite([else_])

			loop.else_ = else_
			assert elsestack == None or elsestack == stack
		else:
			loop.else_ = Suite()

		return suite, stack

	def visitLoopRegion(self, block, stack):
		assert isinstance(stack, PythonStack), stack

		block, loopstack = self.handleLinearRegion(block, stack.duplicate())

		return block, stack

	def visitExceptRegion(self, block, stack):
		# Rollback stack
		oldstack = stack.duplicate()

		block, stack = self.handleLinearRegion(block, stack)

		return block, oldstack

	def visitFinallyRegion(self, block, stack):
		# Rollback stack
		oldstack = stack.duplicate()

		block, stack = self.handleLinearRegion(block, stack)

		return block, oldstack


	def visitEndFinally(self, block, stack):
		assert isinstance(stack, PythonStack), stack
		#assert stack.size() >= 2, stack.size()
		assert stack.size() >= 1, stack.size()

		if stack.peek() == pythonstack.exceptionType:
			# End finally is, without a doubt, reraising an exception.
			stack.discard()
			assert stack.peek() == pythonstack.exceptionValue
			stack.discard()
			assert stack.peek() == pythonstack.exceptionTraceback
			stack.discard()
			# HACK should get rid of the stack
			#stack = None

		# FINALLY prep:
		# PUSH value
		# PUSH enum return / continue

		block = EndFinally()

		block = None # HACK?
		stack = None

		return block, stack

	def extractExceptionHandlers(self, block):
		handlers = []
		else_ = None

		while True:
			if isinstance(block, Suite) and len(block.blocks) >= 2:
				compare 	= block.blocks[-2]
				switch 		= block.blocks[-1]

				if isinstance(switch, Switch) and isinstance(compare, Assign):
					if isinstance(compare.expr, BinaryOp) and compare.expr.op == 'exception match':
						assert compare.expr.left == pythonstack.exceptionType


						# Get rid of the compare
						condition = Suite(block.blocks[:-2])
						exceptiontype = compare.expr.right

						body = switch.t
						next = switch.f

						defn = self.getDefns(body)
						exceptionvalue = defn.get(pythonstack.exceptionValue)

						handler = ExceptionHandler(condition, exceptiontype, exceptionvalue, body)
						handlers.append(handler)

						block = next
						continue

			# Done finding handlers.
			if isinstance(block, EndFinally):
				else_ = None
			else:
				else_ = block
			break

		return handlers, else_

	def visitTryExcept(self, block, stack):
		assert isinstance(stack, PythonStack), stack

		oldstack = stack
		stack = PythonStack()

		### Evaluate the try block ###
		tryblock, stack = self.visit(block.tryBlock, stack)

		if block.elseBlock:
			elseblock, stack = self.visit(block.elseBlock, stack)
		else:
			elseblock = None

		# Restore stack, and prepare for the except block.
		stack = PythonStack()
		stack.push(pythonstack.exceptionTraceback)
		stack.push(pythonstack.exceptionValue)
		stack.push(pythonstack.exceptionType)

		### Evaluate the except block ###
		exceptblock, stack = self.visit(block.exceptBlock, stack)
		if exceptblock == None:
			assert stack
			exceptblock = Suite()

		handlers, default = self.extractExceptionHandlers(exceptblock)

		### Create AST node ###
		# TODO mutate "exception compare" and "end finally" blocks.
		block = TryExceptFinally(tryblock, handlers, default, elseblock, None)

		return block, oldstack

	def visitTryFinally(self, block, stack):
		oldstack = stack

		stack = PythonStack()
		tryblock, stack = self.visit(block.tryBlock, stack)

		stack = PythonStack()
		stack.push(pythonstack.flowInfo)

		finallyblock, stack = self.visit(block.finallyBlock, stack)

		if isinstance(tryblock, TryExceptFinally):
			outblock = tryblock
			outblock.finally_ = finallyblock
		else:
			if not finallyblock:
				# Otherwise it becomes degenerate.
				finallyblock = Suite()
			outblock = TryExceptFinally(tryblock, [], None, None, finallyblock)

		return outblock, oldstack


	def makeLoopMask(self, block):
		# All variables that are written to by the loop are
		# masked, so their values on entry are not used.

		m = self.modifySet(block)

		mask = {}

		for name in m: mask[name] = Local()

		return mask

	def visitForLoop(self, block, stack):
		assert isinstance(stack, PythonStack), stack

		assert block.origin, block

		iterator = stack.peek()
		if isinstance(iterator, pythonstack.Iter):
			iterlcl = iterator.expr
		else:
			assert isinstance(iterator, Local)
			iterlcl = iterator

		# Put the result of iteration on the stack.
		bodystack = stack.duplicate()
		bodystack.push(pythonstack.loopIndex)


		# Evaluate the body.
		bodyBlock, bodystack = self.visit(block.body, bodystack)

		defn = self.getDefns(bodyBlock)
		assert pythonstack.loopIndex in defn, bodyBlock
		index = defn[pythonstack.loopIndex]


		if not isinstance(bodyBlock, Suite):
			bodyBlock = Suite([bodyBlock])

		getNext = GetAttr(iterlcl, Existing(self.extractor.getObject('next')))
		getNext.rewriteAnnotation(origin=block.origin)

		temp = Local()
		loopPreamble = Suite([Assign(getNext, [temp])])

		iterNext = Call(temp, [], [], None, None)
		iterNext.rewriteAnnotation(origin=block.origin)

		if isinstance(index, Local):
			bodyPreamble = Suite([Assign(iterNext, [index])])
		elif isinstance(index, Cell):
			lclTemp = Local(index.name)
			bodyPreamble = Suite([Assign(iterNext, [lclTemp]), SetCellDeref(lclTemp, index)])

			# Force the index to be a local
			index = lclTemp
		else:
			assert False, type(index)

		outblock = For(iterlcl, index, loopPreamble, bodyPreamble, bodyBlock, Suite([]))

		assert stack.peek() == iterator, stack.peek()
		stack.discard() # Pop off the iterator.

		return outblock, stack

	def visitWhileLoop(self, block, stack):
		assert isinstance(stack, PythonStack), stack


		if block.cond:
			condition, tstack, fstack, (maybeTrue, maybeFalse) = self.processCond(block.cond, stack)
		else:
			# Sometimes the condition is const-folded out.
			lcl = Local()
			condition = Condition(Suite([Assign(Existing(self.extractor.getObject(True)), [lcl])]), lcl)
			tstack = stack.duplicate()
			fstack = stack.duplicate()

		# Evaluate the body.
		bodyBlock, bodystack = self.visit(block.body, tstack)

		if not isinstance(bodyBlock, Suite):
			bodyBlock = Suite([bodyBlock])
		outblock = While(condition, bodyBlock, Suite([]))

		return outblock, fstack


	def visitCodeBlock(self, block, stack):
		assert isinstance(stack, PythonStack), stack
		outblock, stack = self.handleLinearRegion(block, stack)
		code = Code('unknown', CodeParameters(Local('internal_self'), (), (), None, None, [Local('internal_return')]), outblock)
		return code, stack


	# External entry point.
	def process(self, block, stack):
		assert isinstance(stack, PythonStack)
		block, stack = self.walk(block, stack)
		return block






def destack(code, mname, fname, root, argnames, vargs, kargs, extractor, callback, trace=False):
	dv = DestackVisitor(code, mname, extractor, callback, trace)

	# Create the locals for each parameter.
	param = []
	for name in argnames:
		assert isinstance(name, str), name
		p = Local(name)
		param.append(p)
		dv.locals[name] = p

	if vargs:
		assert isinstance(vargs, str), vargs
		v = Local(vargs)
		dv.locals[vargs] = v
	else:
		v = None

	if kargs:
		assert isinstance(kargs, str), kargs
		k = Local(kargs)
		dv.locals[kargs] = k
	else:
		k = None

	stack = PythonStack()
	root = dv.process(root, stack)
	root.name = fname

	root.codeparameters.params = param
	root.codeparameters.paramnames = argnames
	root.codeparameters.vparam = v
	root.codeparameters.kparam = k

	origin = codeOrigin(code)
	root.rewriteAnnotation(origin=origin)

	return root
