from __future__ import absolute_import

from util.visitor import StandardVisitor

from language.python.ast import *

from common.defuse import defuse

from . localframe import Merge, LoopMerge, Split, LocalFrame, mergeFrames, Inserter, HeadInserter, TailInserter, ExceptionMerge

import sys
from language.base.dumpast import DumpAST

from . numbering import NumberAST, contains
from . placeflow import PlaceFlowFunctions

from common.errors import InternalError

class HandlerStack(object):
	def __init__(self):
		self.stack = []

	def new(self):
		self.stack.append([])

	def pop(self):
		return self.stack.pop()

	def register(self, suite, frame):
		if not self.stack:
			raise InternalError, "Stack underflow when registering new suite."
		self.stack[-1].append((TailInserter(suite), frame))

class Handlers(object):
	def __init__(self):
		self.breaks 	= HandlerStack()
		self.continues 	= HandlerStack()
		self.returns 	= HandlerStack()
		self.raises	= HandlerStack()
		self.mayExcept 	= HandlerStack()




class SSITransformer(StandardVisitor):
	def __init__(self, annotate, readExcept, hasExceptionHandling):
		super(SSITransformer, self).__init__()
		self.locals = LocalFrame()
		self.handlers = Handlers()

		self.defns = {}

		self.annotate = annotate

		self.exceptLocals = {}

		self.exceptLevel  = 0
		self.exceptRename = []

		self.hasExceptionHandling = hasExceptionHandling

	# HACK to retain annotations
	# TODO rewrite using new framework?
	def visit(self, node, *args):
		result = StandardVisitor.visit(self, node, *args)

		if hasattr(node, 'annotation') and result:
			result.annotation = node.annotation

		return result

	def process(self, node):
		assert self.locals

		if node == None: return None

##		assert not node.onEntry
##		assert not node.onExit

		return self.visit(node)

	def enterExcept(self, r):
		self.exceptLevel += 1

		rn = {}

		if self.exceptLevel > 1:
			rn.update(self.exceptRename[-1])


		merges = Suite([])

		for lcl in r:
			if not lcl in rn:
				old = self.visit(lcl)
				merge = Local(lcl.name)
				rn[lcl] = merge
				asgn = Assign(old, merge)
				asgn.markMerge()
				merges.append(asgn)

		self.exceptRename.append(rn)

		return merges

	def exitExcept(self):
		assert self.exceptLevel > 0
		self.exceptLevel -= 1
		rn = self.exceptRename[-1]
		self.exceptRename.pop()

		return rn

	def exceptLocal(self, lcl):
		if not lcl in self.exceptLocals:
			self.exceptLocals[lcl] = Local(lcl.name)
		return self.exceptLocals[lcl]
		#return self.exceptRename[-1].get(lcl)


	def reach(self, lcl):
		while lcl in self.defns and isinstance(self.defns[lcl], Local):
			lcl = self.defns[lcl]
		return lcl

	def default(self, node):
		# TODO: should be process instead of visit?
		children = [self.visit(child) for child in node.children()]
		return type(node)(*children)

	def visitstr(self, node):
		return node

	def visitint(self, node):
		return node

	def visitNoneType(self, node):
		return node

	def visittuple(self, node):
		return tuple([self.visit(i) for i in node])

	def visitlist(self, node):
		return [self.visit(i) for i in node]


	def visitExisting(self, node):
		return node

	def visitLocal(self, node):
		lcl = self.locals.readLocal(node)
		assert lcl, (node, self.locals.lut, self.original)

		lcl = self.reach(lcl)
		assert lcl, (node, self.defns)

		return lcl

	def visitCell(self, node):
		return node

	def visitDelete(self, node):
##		lcl = self.process(node.lcl)
##		self.locals.deleteLocal(node.lcl)
##		return Delete(lcl)

		# Delete is meaningless once we SSA the code.
		return None


##	def visitRaise(self, node):
##		return Raise(self.process(node.exception), self.process(node.parameter), self.process(node.traceback))

	def visitUnpackSequence(self, node):
		expr = self.process(node.expr)
		targets = [self.locals.writeLocal(target) for target in node.targets]
		out = UnpackSequence(expr, targets)

		if self.hasExceptionHandling:
			out = Suite([out])

			for oldtgt, newtgt in zip(node.targets, targets):
				asgn = Assign(newtgt, self.exceptLocal(oldtgt))
				asgn.markMerge()
				out.append(asgn)

		return out

	def visitCondition(self, node):
		# HACK
		try:
			preamble = self.process(node.preamble)
			conditional = self.process(node.conditional)
			newnode = Condition(preamble, conditional)
		except AssertionError:
			raise
			#raise Exception, repr(node) + '\n\n' + repr(self.locals.lut)

		return newnode

	def visitSwitch(self, node):
		condition = self.process(node.condition)

		normal = []

		# Split

		tf, ff = self.locals.split()

		self.locals = tf
		t = self.process(node.t)
		tf = self.locals
		if tf:
			normal.append((TailInserter(t), tf))


		self.locals = ff
		f = self.process(node.f)
		ff = self.locals
		if ff:
			normal.append((TailInserter(f), ff))

		self.locals = mergeFrames(normal)

		newnode = Switch(condition, t, f)

		return newnode

	def visitAssign(self, node):
		assert self.locals

		if len(self.localuses[node.lcl]) > 0:
			assert isinstance(node.lcl, Local)

			expr = self.process(node.expr)

			assert self.locals, node.expr

			if isinstance(node.expr, Local):
				# Assign local to local.  Nullop for SSA.

				expr = self.reach(expr)
				self.locals.redefineLocal(node.lcl, expr)

				# Create a merge for exception handling.
				if self.hasExceptionHandling:
					el = self.exceptLocal(node.lcl)
					easgn = Assign(expr, el)
					easgn.markMerge()
					return easgn
				else:
					return None


			else:
				rename = self.locals.writeLocal(node.lcl)
				assert not rename in self.defns
				self.defns[rename] = expr


				asgn = Assign(expr, rename)

				if self.hasExceptionHandling:
					# Create a merge for exception handling.
					el = self.exceptLocal(node.lcl)
					easgn = Assign(rename, el)
					easgn.markMerge()
					asgn = Suite([asgn, easgn])

				return asgn

		elif not node.expr.isPure():
			return Discard(self.process(node.expr))
		else:
			return None

	def __register(self, suite, handler):
		if handler:
			handler.register(suite, self.locals)
			self.locals = None


	def registerFrame(self, suite):
		if self.locals:
			blocks = suite.blocks
			if blocks:
				if isinstance(blocks[-1], Break):
					handler = self.handlers.breaks
				elif isinstance(blocks[-1], Continue):
					handler = self.handlers.continues
				elif isinstance(blocks[-1], Return):
					handler = self.handlers.returns
				elif isinstance(blocks[-1], Raise):
					handler = self.handlers.raises
				else:
					handler = None

				self.__register(suite, handler)


	def visitSuite(self, node):
		blocks = []
		for block in node.blocks:
			assert self.locals
			blocks.append(self.process(block))

		newnode =  Suite(blocks)
		self.registerFrame(newnode)

		return newnode

	def visitExceptionHandler(self, node):
		preamble = self.process(node.preamble)
		type = self.process(node.type)

		if isinstance(node.value, Local):
			value = self.locals.writeLocal(node.value)
		else:
			value = self.process(node.value)

		body = self.process(node.body)

		return ExceptionHandler(preamble, type, value, body)

	def visitTryExceptFinally(self, node):
		if node.finally_:
			self.handlers.breaks.new()
			self.handlers.continues.new()
			self.handlers.returns.new()
			self.handlers.raises.new()

		r, m, fr, fm = self.annotate[node]


		body = self.process(node.body)


		normal = self.locals

		merges = []

		# Raise / may raise
		handlers = []
		for handler in node.handlers:
			self.locals = ef = LocalFrame(ExceptionMerge(self.exceptLocals))
			h = self.process(handler)
			handlers.append(h)
			merges.append((TailInserter(h.body), self.locals))


		self.locals = ef = LocalFrame(ExceptionMerge(self.exceptLocals))
		default = self.process(node.defaultHandler)
		merges.append((TailInserter(default), self.locals))


		# Normal
		self.locals = normal
		else_ 	= self.process(node.else_)

		if not else_:
			else_ = Suite([])

		merges.append((TailInserter(else_), self.locals))

		self.locals = mergeFrames(merges)

		if node.finally_:
			breaks = self.handlers.breaks.pop()
			continues = self.handlers.continues.pop()
			returns = self.handlers.returns.pop()
			raises = self.handlers.raises.pop()

		# All paths
		finally_ = self.process(node.finally_)

		newnode = TryExceptFinally(body, handlers, default, else_, finally_)

		return newnode

	def makeLoopMerge(self, lcls, read, hot, modify):
		entrySuite = Suite([]) # Holds the partial merges (entry -> condition)
		loopMerge = LoopMerge(HeadInserter(entrySuite), lcls, read, hot, modify)
		lcls = LocalFrame(loopMerge)
		return entrySuite, loopMerge, lcls

	def handleWhileBody(self, node, lcls):
		self.locals = lcls

		self.handlers.breaks.new()
		self.handlers.continues.new()

		body = self.process(node.body)

		breaks = self.handlers.breaks.pop()
		continues = self.handlers.continues.pop()

		return body, continues, breaks


	def visitWhile(self, node):
		read, hot, modify, breakmerge = self.annotate[node]

		entrySuite, loopMerge, lcls  = self.makeLoopMerge(self.locals, read, hot, modify)


		self.locals = lcls
		condition = self.process(node.condition)

		bodylcls, exitlcls = lcls.split()

		body, continues, breaks = self.handleWhileBody(node, bodylcls)

		# Finalize loop merge w/ continues and normal.
		continues.append((TailInserter(body), self.locals))
		loopMerge.finalize(continues)

		# Process the normal loop exit into else
		self.locals = exitlcls
		else_ = self.process(node.else_)

		# Merge in breaks.
		breaks.append((TailInserter(else_), self.locals))
		self.locals = mergeFrames(breaks)


		# Create the ast node
		newnode = While(condition, body, else_)

		# Suite contains entry splits/merges.
		entrySuite.append(newnode)
		return entrySuite

	def handleForBody(self, node, lcls):
		self.locals = lcls

		self.handlers.breaks.new()
		self.handlers.continues.new()


		#if isinstance(node.index, Local):
		#	index = self.locals.writeLocal(node.index)
		#else:

		bodyPreamble = self.process(node.bodyPreamble)

		# HACK
		# The index may not be assigned if it is unused.
		if not node.index in self.locals.lut:
			index = node.index
		else:
			index 	= self.process(node.index)

		body = self.process(node.body)

		breaks = self.handlers.breaks.pop()
		continues = self.handlers.continues.pop()


		return index, bodyPreamble, body, continues, breaks




	def visitFor(self, node):
		loopPreamble = self.process(node.loopPreamble)
		iterator = self.process(node.iterator)

		read, hot, modify, breakmerge = self.annotate[node]

		entrySuite, loopMerge, lcls  = self.makeLoopMerge(self.locals, read, hot, modify)

		bodylcls, exitlcls = lcls.split()

		index, bodyPreamble, body, continues, breaks = self.handleForBody(node, bodylcls)

		# Finalize loop merge w/ continues and normal.
		continues.append((TailInserter(body), self.locals))
		loopMerge.finalize(continues)

		# Process the normal loop exit into else
		self.locals = exitlcls
		else_ = self.process(node.else_)

		# Merge in breaks.
		breaks.append((TailInserter(else_), self.locals))
		self.locals = mergeFrames(breaks)


		# Create the ast node
		newnode = For(iterator, index, loopPreamble, bodyPreamble, body, else_)

		# Suite contains entry splits/merges.
		entrySuite.append(newnode)
		return entrySuite

	def visitCode(self, node):
		# Insulate any containing functions.
		old = self.locals

		self.locals = LocalFrame()

		self.handlers.returns.new()

		selfparam = self.locals.writeLocal(node.selfparam) if node.selfparam else None

		params = [self.locals.writeLocal(p) for p in node.parameters]

		vparam = self.locals.writeLocal(node.vparam) if node.vparam else None
		kparam = self.locals.writeLocal(node.kparam) if node.kparam else None

		ast = self.process(node.ast)

		# Mutate the code
		node.selfparam = selfparam
		node.parameters = params
		node.vparam = vparam
		node.kparam = kparam
		node.ast = ast

		returns = self.handlers.returns.pop()

		self.locals = old

		return node

	def transform(self, node):
		(defines, uses), (globaldefines, globaluses), collapsable = defuse(node)

		self.localdefs = defines
		self.localuses = uses
		self.collapsable = collapsable

		self.original = node # HACK for debugging

		return self.process(node)



def ssiTransform(node):
	na = NumberAST()
	na.walk(node)

	pff = PlaceFlowFunctions(na.numbering)
	pff.walk(node)

	# HACK
	if pff.hasExceptionHandling:
		return node

	if False:
		nt = NewTransformer(pff.annotate)
		node = nt.walk(node)
	else:
		ssit = SSITransformer(pff.annotate, pff.exceptRead, pff.hasExceptionHandling)
		node = ssit.transform(node)

	return node
