from __future__ import absolute_import

from util.typedispatch import *
from language.python import ast, defuse

from . localframe import Merge, LoopMerge, Split, LocalFrame, mergeFrames, Inserter, HeadInserter, TailInserter, ExceptionMerge

import sys

from . numbering import NumberAST, contains
from . placeflow import PlaceFlowFunctions

from application.errors import InternalError

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




class SSITransformer(TypeDispatcher):
	__namedispatch__ = True # HACK emulates old visitor

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

	def enterExcept(self, r):
		self.exceptLevel += 1

		rn = {}

		if self.exceptLevel > 1:
			rn.update(self.exceptRename[-1])


		merges = ast.Suite([])

		for lcl in r:
			if not lcl in rn:
				old = self(lcl)
				merge = lcl.clone()
				rn[lcl] = merge
				asgn = ast.Assign(old, merge)
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
			self.exceptLocals[lcl] = lcl.clone()
		return self.exceptLocals[lcl]

	def reach(self, lcl):
		while lcl in self.defns and isinstance(self.defns[lcl], ast.Local):
			lcl = self.defns[lcl]
		return lcl

	@defaultdispatch
	def default(self, node):
		return node.rewriteChildren(self)

	@dispatch(str, int, type(None))
	def visitLeaf(self, node):
		return node

	@dispatch(list, tuple)
	def visitContainer(self, node):
		return [self(child) for child in node]

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
##		lcl = self(node.lcl)
##		self.locals.deleteLocal(node.lcl)
##		return Delete(lcl)

		# Delete is meaningless once we SSA the code.
		return None

##	def visitRaise(self, node):
##		return Raise(self(node.exception), self(node.parameter), self(node.traceback))

	def visitUnpackSequence(self, node):
		expr = self(node.expr)
		targets = [self.locals.writeLocal(target) for target in node.targets]
		out = node.reconstruct(expr, targets)

		if self.hasExceptionHandling:
			out = ast.Suite([out])

			for oldtgt, newtgt in zip(node.targets, targets):
				asgn = ast.Assign(newtgt, self.exceptLocal(oldtgt))
				asgn.markMerge()
				out.append(asgn)

		return out

	def visitCondition(self, node):
		# HACK
		try:
			preamble    = self(node.preamble)
			conditional = self(node.conditional)
			newnode     = node.reconstruct(preamble, conditional)
		except AssertionError:
			raise
			#raise Exception, repr(node) + '\n\n' + repr(self.locals.lut)

		return newnode

	def visitSwitch(self, node):
		condition = self(node.condition)

		normal = []

		# Split

		tf, ff = self.locals.split()

		self.locals = tf
		t = self(node.t)
		tf = self.locals
		if tf:
			normal.append((TailInserter(t), tf))


		self.locals = ff
		f = self(node.f)
		ff = self.locals
		if ff:
			normal.append((TailInserter(f), ff))

		self.locals = mergeFrames(normal)

		return node.reconstruct(condition, t, f)

	def visitAssign(self, node):
		assert self.locals

		if any([len(self.localuses[lcl]) > 0 for lcl in node.lcls]):
			expr = self(node.expr)

			assert self.locals, node.expr

			if isinstance(node.expr, ast.Local):
				# Assign local to local.  Nullop for SSA.
				assert len(node.lcls) == 1

				expr = self.reach(expr)
				self.locals.redefineLocal(node.lcls[0], expr)

				# Create a merge for exception handling.
				if self.hasExceptionHandling:
					el = self.exceptLocal(node.lcls[0])
					easgn = ast.Assign(expr, el)
					easgn.markMerge()
					return easgn
				else:
					return None


			else:
				renames = [self.locals.writeLocal(lcl) for lcl in node.lcls]
				for rename in renames:
					self.defns[rename] = expr

				asgn = ast.Assign(expr, renames)

				if self.hasExceptionHandling:
					# Create a merge for exception handling.
					output = [asgn]
					for lcl, rename in zip(node.lcls, renames):
						el = self.exceptLocal(lcl)
						easgn = ast.Assign(rename, el)
						easgn.markMerge()
						output.append(easgn)
					asgn = ast.Suite(output)

				return asgn

		elif not node.expr.isPure():
			return ast.Discard(self(node.expr))
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
				if isinstance(blocks[-1], ast.Break):
					handler = self.handlers.breaks
				elif isinstance(blocks[-1], ast.Continue):
					handler = self.handlers.continues
				elif isinstance(blocks[-1], ast.Return):
					handler = self.handlers.returns
				elif isinstance(blocks[-1], ast.Raise):
					handler = self.handlers.raises
				else:
					handler = None

				self.__register(suite, handler)

	@dispatch(ast.Suite)
	def visitSuite(self, node):
		blocks = []
		for block in node.blocks:
			assert self.locals
			blocks.append(self(block))

		newnode = node.reconstruct(blocks)
		self.registerFrame(newnode)
		return newnode

	def visitExceptionHandler(self, node):
		preamble = self(node.preamble)
		type = self(node.type)

		if isinstance(node.value, ast.Local):
			value = self.locals.writeLocal(node.value)
		else:
			value = self(node.value)

		body = self(node.body)

		return node.reconstruct(preamble, type, value, body)

	def visitTryExceptFinally(self, node):
		if node.finally_:
			self.handlers.breaks.new()
			self.handlers.continues.new()
			self.handlers.returns.new()
			self.handlers.raises.new()

		r, m, fr, fm = self.annotate[node]


		body = self(node.body)


		normal = self.locals

		merges = []

		# Raise / may raise
		handlers = []
		for handler in node.handlers:
			self.locals = ef = LocalFrame(ExceptionMerge(self.exceptLocals))
			h = self(handler)
			handlers.append(h)
			merges.append((TailInserter(h.body), self.locals))


		self.locals = ef = LocalFrame(ExceptionMerge(self.exceptLocals))
		default = self(node.defaultHandler)
		merges.append((TailInserter(default), self.locals))


		# Normal
		self.locals = normal
		else_ 	= self(node.else_)

		if not else_:
			else_ = ast.Suite([])

		merges.append((TailInserter(else_), self.locals))

		self.locals = mergeFrames(merges)

		if node.finally_:
			breaks = self.handlers.breaks.pop()
			continues = self.handlers.continues.pop()
			returns = self.handlers.returns.pop()
			raises = self.handlers.raises.pop()

		# All paths
		finally_ = self(node.finally_)

		return node.reconstruct(body, handlers, default, else_, finally_)

	def makeLoopMerge(self, lcls, read, hot, modify):
		entrySuite = ast.Suite([]) # Holds the partial merges (entry -> condition)
		loopMerge = LoopMerge(HeadInserter(entrySuite), lcls, read, hot, modify)
		lcls = LocalFrame(loopMerge)
		return entrySuite, loopMerge, lcls

	def handleWhileBody(self, node, lcls):
		self.locals = lcls

		self.handlers.breaks.new()
		self.handlers.continues.new()

		body = self(node.body)

		breaks = self.handlers.breaks.pop()
		continues = self.handlers.continues.pop()

		return body, continues, breaks


	def visitWhile(self, node):
		read, hot, modify, breakmerge = self.annotate[node]

		entrySuite, loopMerge, lcls  = self.makeLoopMerge(self.locals, read, hot, modify)


		self.locals = lcls
		condition = self(node.condition)

		bodylcls, exitlcls = lcls.split()

		body, continues, breaks = self.handleWhileBody(node, bodylcls)

		# Finalize loop merge w/ continues and normal.
		continues.append((TailInserter(body), self.locals))
		loopMerge.finalize(continues)

		# Process the normal loop exit into else
		self.locals = exitlcls
		else_ = self(node.else_)

		# Merge in breaks.
		breaks.append((TailInserter(else_), self.locals))
		self.locals = mergeFrames(breaks)


		# Create the ast node
		newnode = node.reconstruct(condition, body, else_)

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

		bodyPreamble = self(node.bodyPreamble)

		# HACK
		# The index may not be assigned if it is unused.
		if not node.index in self.locals.lut:
			index = node.index
		else:
			index 	= self(node.index)

		body = self(node.body)

		breaks = self.handlers.breaks.pop()
		continues = self.handlers.continues.pop()


		return index, bodyPreamble, body, continues, breaks




	def visitFor(self, node):
		loopPreamble = self(node.loopPreamble)
		iterator = self(node.iterator)

		read, hot, modify, breakmerge = self.annotate[node]

		entrySuite, loopMerge, lcls  = self.makeLoopMerge(self.locals, read, hot, modify)

		bodylcls, exitlcls = lcls.split()

		index, bodyPreamble, body, continues, breaks = self.handleForBody(node, bodylcls)

		# Finalize loop merge w/ continues and normal.
		continues.append((TailInserter(body), self.locals))
		loopMerge.finalize(continues)

		# Process the normal loop exit into else
		self.locals = exitlcls
		else_ = self(node.else_)

		# Merge in breaks.
		breaks.append((TailInserter(else_), self.locals))
		self.locals = mergeFrames(breaks)


		# Create the ast node
		newnode = node.reconstruct(iterator, index, loopPreamble, bodyPreamble, body, else_)

		# Suite contains entry splits/merges.
		entrySuite.append(newnode)
		return entrySuite

	def processCode(self, node):
		assert isinstance(node, ast.Code), type(node)

		# Insulate any containing functions.
		old = self.locals

		self.locals = LocalFrame()

		self.handlers.returns.new()

		p = node.codeparameters

		selfparam = self.locals.writeLocal(p.selfparam) if p.selfparam else None

		params = [self.locals.writeLocal(param) for param in p.params]

		vparam = self.locals.writeLocal(p.vparam) if p.vparam else None
		kparam = self.locals.writeLocal(p.kparam) if p.kparam else None

		body = self(node.ast)

		# Mutate the code
		selfparam = selfparam
		parameters = params
		parameternames = p.paramnames
		defaults = p.defaults
		vparam = vparam
		kparam = kparam
		returnparams = p.returnparams

		node.codeparameters = node.codeparameters.reconstruct(selfparam, parameters, parameternames, defaults, vparam, kparam, returnparams)
		node.ast = body

		returns = self.handlers.returns.pop()

		self.locals = old

		return node

	def transform(self, node):
		(defines, uses), (globaldefines, globaluses) = defuse.evaluateCode(None, node)

		self.localdefs = defines
		self.localuses = uses

		self.original = node # HACK for debugging

		return self.processCode(node)



def ssiTransform(node):
	na = NumberAST()
	na.process(node)

	pff = PlaceFlowFunctions(na.numbering)
	pff.process(node)

	# HACK
	if pff.hasExceptionHandling:
		return node

	ssit = SSITransformer(pff.annotate, pff.exceptRead, pff.hasExceptionHandling)
	node = ssit.transform(node)

	return node
