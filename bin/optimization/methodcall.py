from util.typedispatch import *
from language.python import ast
from language.python import annotations

from analysis import tools
import dataflow.forward

import optimization.simplify


def contextsThatOnlyInvoke(funcs, invocations):
	output = set()

	# HACK There's only one op in the object getter that will invoke?
	for func in funcs:
		for op in tools.codeOps(func):
			invokes = op.annotation.invokes
			if invokes is not None:
				for cindex, context in enumerate(func.annotation.contexts):
					cinvokes = invokes[1][cindex]

					invokesSet = set(cinvokes)
					match = invokesSet.intersection(invocations)

					# There must be invocations, and they must all be to fget.
					if match and match == invokesSet:
						output.add((func, context))
	return output

def opThatInvokes(func):
	# Find the single op in the function that invokes.
	invokeOp = None
	for op in tools.codeOps(func):
		invokes = op.annotation.invokes
		if invokes is not None and invokes[0]:
			assert invokeOp is None
			invokeOp = op
	assert invokeOp
	return invokeOp

class MethodPatternFinder(TypeDispatcher):
	def findOriginals(self, extractor):
		exports = extractor.stubs.exports
		self.iget = exports['interpreter_getattribute']
		self.oget = exports['object__getattribute__']

		fgetpyobj = exports['function__get__']
		fgetobj = extractor.getObject(fgetpyobj)
		self.fget = extractor.getCall(fgetobj)

		if self.fget is None: return False

		self.mdget = exports['methoddescriptor__get__']

		self.icall = exports['interpreter_call']
		self.mcall = exports['method__call__']

		assert self.iget.annotation.origin
		assert self.oget.annotation.origin
		assert self.fget.annotation.origin
		assert self.mdget.annotation.origin

		assert self.icall.annotation.origin
		assert self.mcall.annotation.origin

		return True


	def findExisting(self, liveCode):
		self.fgets = set()
		self.ogets = set()
		self.igets = set()

		self.icalls = set()
		self.mcalls = set()


		igetO  = self.iget.annotation.origin
		ogetO  = self.oget.annotation.origin
		fgetO  = self.fget.annotation.origin
		mdgetO = self.mdget.annotation.origin

		icallO = self.icall.annotation.origin
		mcallO = self.mcall.annotation.origin


		for code in liveCode:
			origin = code.annotation.origin

			if origin is igetO:  self.igets.add(code)
			if origin is ogetO:  self.ogets.add(code)
			if origin is fgetO:  self.fgets.add(code)
			if origin is mdgetO: self.fgets.add(code)

			if origin is icallO: self.icalls.add(code)
			if origin is mcallO: self.mcalls.add(code)

	def findContexts(self):
		### Get patterns ###
		if not self.fgets: return False
		self.fgetsC = set()
		for func in self.fgets:
			for context in func.annotation.contexts:
				self.fgetsC.add((func, context))

		# HACK There's only one op in the object getter that will invoke?
		self.ogetsC = contextsThatOnlyInvoke(self.ogets, self.fgetsC)
		if not self.ogetsC: return False


		self.igetsC = contextsThatOnlyInvoke(self.igets, self.ogetsC)
		if not self.igetsC: return False


		### Call patterns ###
		if not self.mcalls: return False
		self.mcallsC = set()
		for code in self.mcalls:
			for context in code.annotation.contexts:
				self.mcallsC.add((code, context))

		self.icallsC = contextsThatOnlyInvoke(self.icalls, self.mcallsC)
		if not self.icallsC: return False

		self.buildInvokeLUT()

		return True

	def buildInvokeLUT(self):
		self.invokeLUT = {}

		for code, context in self.mcallsC:
			cindex = code.annotation.contexts.index(context)
			op = opThatInvokes(code)
			targets = op.annotation.invokes[1][cindex]
			self.invokeLUT[(code, context)] = targets

		for code, context in self.icallsC:
			cindex = code.annotation.contexts.index(context)
			op = opThatInvokes(code)
			targets = op.annotation.invokes[1][cindex]

			reach = set()
			for target in targets:
				reach.update(self.invokeLUT[target])
			self.invokeLUT[(code, context)] = annotations.annotationSet(reach)


	def preprocess(self, compiler):
		if not self.findOriginals(compiler.extractor):
			return False
		self.findExisting(compiler.liveCode)
		return self.findContexts()


	def isMethodGetter(self, node, invokes):
		invokes = frozenset(invokes)

		marked = invokes.intersection(self.igetsC)

		if marked and marked == invokes:
			return True
		else:
			return False

	@defaultdispatch
	def default(self, node, invokes):
		return False, None, None

	@dispatch(ast.Call, ast.DirectCall)
	def visitCall(self, node, invokes):
		if len(node.args) == 2 and not node.kwds and not node.vargs and not node.kargs:
			if self.isMethodGetter(node, invokes):
				return True, node.args[0], node.args[1]
		return False, None, None

	@dispatch(ast.GetAttr)
	def visitGetAttr(self, node, invokes):
		if self.isMethodGetter(node, invokes):
			return True, node.expr, node.name
		else:
			return False, None, None

class MethodAnalysis(TypeDispatcher):
	def __init__(self, pattern):
		self.pattern = pattern

	def target(self, node):
		assert isinstance(node, ast.Local), type(node)

		# Kill on expr or name redefinition.
		key = self.flow.lookup(('expr', node))
		if isinstance(key, tuple):
			self.kill(key)

		key = self.flow.lookup(('name', node))
		if isinstance(key, tuple):
			self.kill(key)

	def targets(self, nodes):
		for node in nodes:
			self.target(node)

	def arg(self, node):
		assert isinstance(node, ast.Local), type(node)
		# Kill on method leak.
		key = self.flow.lookup(('meth', node))
		if isinstance(key, tuple):
			self.kill(key)

	def kill(self, key):
		expr, name, meth = key

		check = self.flow.lookup(('expr', expr))
		assert check == key, (check, key)

		check = self.flow.lookup(('name', name))
		assert check == key, (check, key)

		check = self.flow.lookup(('meth', meth))
		assert check == key, (check, key)

		self.flow.undefine(('expr', expr))
		self.flow.undefine(('name', name))
		self.flow.undefine(('meth', meth))

	@dispatch(ast.Local)
	def visitLocal(self, node):
		self.arg(node)

	# ast.Code is a leaf due to direct calls.
	@dispatch(ast.leafTypes, ast.Existing, ast.BuildList, ast.Allocate,
			ast.GetGlobal, ast.Code,
			ast.Break, ast.Continue, ast.DoNotCare, ast.Is)
	def visitLeaf(self, node):
		return node

	@dispatch(ast.Load, ast.Store, ast.Check, ast.Return, ast.SetAttr,
		  ast.SetGlobal, ast.GetSubscript, ast.SetSubscript,
		  ast.Discard, ast.GetIter,
		  ast.ConvertToBool, ast.Not,
		  ast.BinaryOp, ast.UnaryPrefixOp,
		  ast.BuildTuple, ast.Call, ast.DirectCall, ast.MethodCall, ast.GetAttr)
	def visitMayLeak(self, node):
		node.visitChildren(self)
		return node

	@dispatch(ast.Assign)
	def visitAssign(self, node):
		self(node.expr)
		self.targets(node.lcls)

		if not isinstance(node.expr, (ast.Local, ast.Existing)):
			invokes = node.expr.annotation.invokes
			if invokes is not None:
				flag, expr, name = self.pattern(node.expr, invokes[0])

				if flag and len(node.lcls) == 1:
					lcl = node.lcls[0]
					key = (expr, name, lcl)
					self.flow.define(('expr', expr), key)
					self.flow.define(('name', name), key)
					self.flow.define(('meth', lcl), key)

		return node

	@dispatch(ast.UnpackSequence)
	def visitUnpackSequence(self, node):
		self(node.expr)
		for target in node.targets:
			self.target(target)
		return node

	@dispatch(ast.Delete)
	def visitDelete(self, node):
		self.target(node.expr)
		return node

class MethodRewrite(TypeDispatcher):
	def __init__(self, pattern):
		self.pattern = pattern
		self.rewritten = set()

	@defaultdispatch
	def default(self, node):
		return node

	def isMethodCall(self, node, meth):
		invokes = node.annotation.invokes
		if invokes is not None:
			if self.pattern.icallsC.issuperset(invokes[0]):
				key = self.flow.lookup(('meth', meth))
				if isinstance(key, tuple):
					expr, name, meth = key
					return True, expr, name

		return False, None, None

	def transferOpInfo(self, node, rewrite):
		invokes = node.annotation.invokes
		if invokes is not None:
			cinvokesNew = []
			for cinvokes in invokes[1]:
				cinvokesM = set()
				for f, c in cinvokes:
					newinv = self.pattern.invokeLUT[(f, c)]
					cinvokesM.update(newinv)
				cinvokesNew.append(annotations.annotationSet(cinvokesM))

			invokes = annotations.makeContextualAnnotation(cinvokesNew)
			rewrite.annotation = node.annotation.rewrite(invokes=invokes)
		else:
			rewrite.annotation = node.annotation

	def rewriteCall(self, node, expr, name):
		rewrite = ast.MethodCall(expr, name, node.args, node.kwds, node.vargs, node.kargs)
		self.transferOpInfo(node, rewrite)
		self.rewritten.add(id(node))
		return rewrite



	@dispatch(ast.Call)
	def visitCall(self, node):
		meth, expr, name = self.isMethodCall(node, node.expr)
		if meth:
			return self.rewriteCall(node, expr, name)
		return node

	@dispatch(ast.DirectCall)
	def visitDirectCall(self, node):
		meth, expr, name = self.isMethodCall(node, node.selfarg)
		if meth:
			return self.rewriteCall(node, expr, name)
		return node

	@dispatch(ast.Assign, ast.Discard)
	def visitStatement(self, node):
		return node.rewriteChildren(self)

def methodMeet(values):
	prototype = values[0]
	for value in values:
		if value != prototype:
			return dataflow.forward.top
	return prototype

def evaluate(compiler):
	with compiler.console.scope('method call'):
		pattern = MethodPatternFinder()
		if not pattern.preprocess(compiler):
			compiler.console.output("No method calls to fuse.")
			return

		numrewritten = 0
		for code in compiler.liveCode:
			analyze = MethodAnalysis(pattern)
			rewrite = MethodRewrite(pattern)

			meet = methodMeet

			traverse = dataflow.forward.ForwardFlowTraverse(meet, analyze, rewrite)
			t = dataflow.forward.MutateCode(traverse)

			# HACK
			analyze.flow = traverse.flow
			rewrite.flow = traverse.flow

			t(code)

			# HACK to turn attribute access assignments into discards.
			if rewrite.rewritten:
				optimization.simplify.evaluateCode(compiler, code)

			if rewrite.rewritten:
				numrewritten += len(rewrite.rewritten)

		# TODO may not be entirely correct, as the method call may
		# not be fused in the final iteration.
		compiler.console.output("%d method calls fused." % numrewritten)
