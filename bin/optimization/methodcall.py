from util.typedispatch import *
from programIR.python import ast
from util import xform

import dataflow.forward


import util.xtypes

import optimization.simplify
import analysis.analysisdatabase
analysis.analysisdatabase.DummyAnalysisDatabase

def contextsThatOnlyInvoke(adb, funcs, invocations):
	output = set()

	db = adb.db

	# HACK There's only one op in the object getter that will invoke?
	for func in funcs:
		funcinfo = db.functionInfo(func)
		for op in adb.functionOps(func):
			opinfo = funcinfo.opInfo(op)
			if opinfo.merged.invokes:
				for context, cinfo in opinfo.contexts.iteritems():
					invokes = set()
					for dc, df in cinfo.invokes:
						invokes.add((df, dc))

					match = invokes.intersection(invocations)

					# There must be invocations, and they must all be to fget.
					if match and match == invokes:
						output.add((func, context))
	return output

def opThatInvokes(adb, func):
	# Find the single op in the function that invokes.
	invokeOp = None
	funcinfo = adb.db.functionInfo(func)
	for op in adb.functionOps(func):
		opinfo = funcinfo.opInfo(op)
		if opinfo.merged.invokes:
			assert invokeOp is None
			invokeOp = op
	assert invokeOp
	return invokeOp

class MethodPatternFinder(object):
	__metaclass__ = typedispatcher

	def findOriginals(self, extractor):
		exports = extractor.stubs.exports
		self.iget = exports['interpreter_getattribute']
		self.oget = exports['object__getattribute__']

		fgetpyobj = exports['function__get__']
		fgetobj = extractor.getObject(fgetpyobj)
		self.fget = extractor.getCall(fgetobj)

		self.mdget = exports['methoddescriptor__get__']

		self.mcall = exports['method__call__']


	def findExisting(self, adb):
		db = adb.db

		self.fgets = set()
		self.ogets = set()
		self.igets = set()

		for func, funcinfo in db.functionInfos.iteritems():
			original = funcinfo.original
			if original is self.iget: self.igets.add(func)
			if original is self.oget: self.ogets.add(func)
			if original is self.fget: self.fgets.add(func)
			if original is self.mdget: self.fgets.add(func)


	def findContexts(self, adb):
		db = adb.db
		if not self.fgets: return False

		self.fgetsC = set()
		self.ogetsC = set()
		self.igetsC = set()
		for func in self.fgets:
			funcinfo = db.functionInfo(func)
			for context in funcinfo.contexts:
				self.fgetsC.add((func, context))

		# HACK There's only one op in the object getter that will invoke?
		self.ogetsC = contextsThatOnlyInvoke(adb, self.ogets, self.fgetsC)
		if not self.ogetsC: return False


		self.igetsC = contextsThatOnlyInvoke(adb, self.igets, self.ogetsC)
		if not self.igetsC: return False

		return True


	def preprocess(self, extractor, adb):
		self.findOriginals(extractor)
		self.findExisting(adb)
		return self.findContexts(adb)


	def isMethodGetter(self, node, invokes):
		#invokes = self.info.opInfo(node).merged.invokes
		invokes = frozenset([(f, c) for c, f in invokes]) # Flip the info.

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
	def visitCall(self, node, invokes):
		if self.isMethodGetter(node, invokes):
			return True, node.expr, node.name
		else:
			return False, None, None

class MethodAnalysis(object):
	__metaclass__ = typedispatcher

	def __init__(self, info, pattern):
		self.info = info
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


	@defaultdispatch
	def default(self, node):
		assert False, type(node)

	@dispatch(ast.Local)
	def visitLocal(self, node):
		self.arg(node)

	# ast.Code is a leaf due to direct calls.
	@dispatch(ast.Existing, str, ast.BuildList, ast.Allocate,
			ast.GetGlobal, type(None), ast.Code,
			ast.Break, ast.Continue,)
	def visitLeaf(self, node):
		return node

	@dispatch(ast.Load, ast.Store, ast.Check, ast.Return, ast.SetAttr,
		  ast.SetGlobal, ast.GetSubscript, ast.SetSubscript,
		  ast.Discard, ast.GetIter,
		  ast.ConvertToBool, ast.Not,
		  ast.BinaryOp, ast.UnaryPrefixOp,
		  ast.BuildTuple, list, ast.Call, ast.DirectCall, ast.MethodCall, ast.GetAttr)
	def visitMayLeak(self, node):
		xform.visitAllChildren(self, node)
		return node

	@dispatch(ast.Assign)
	def visitAssign(self, node):
		self(node.expr)

		self.target(node.lcl)

		invokes = self.info.opInfo(node.expr).merged.invokes
		if invokes:
			flag, expr, name = self.pattern(node.expr, invokes)

			if flag:
				key = (expr, name, node.lcl)
				self.flow.define(('expr', expr), key)
				self.flow.define(('name', name), key)
				self.flow.define(('meth', node.lcl), key)

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

class MethodRewrite(object):
	__metaclass__ = typedispatcher

	def __init__(self, adb, info, pattern):
		self.adb     = adb
		self.info    = info
		self.pattern = pattern

		self.rewritten = set()

	@defaultdispatch
	def default(self, node):
		return node

	def isMethodCall(self, node, meth):
		invokes = self.info.opInfo(node).merged.invokes

		# HACK should be considering funcinfo.original, not the function itself.
		originalFuncs = frozenset([f for c, f in invokes])
		if originalFuncs == frozenset([self.pattern.mcall]):
			key = self.flow.lookup(('meth', node.expr))
			if isinstance(key, tuple):
				expr, name, meth = key
				return True, expr, name

		return False, None, None

	def transferOpInfo(self, node, rewrite):
		srcInfo = self.info.opInfo(node)
		dstInfo = self.info.opInfo(rewrite)

		for context, srccopinfo in srcInfo.contexts.iteritems():
			dstcopinfo = dstInfo.context(context)

			dstcopinfo.references.update(srccopinfo.references)
			#dstcopinfo.reads.update(srccopinfo.reads)
			#dstcopinfo.modifies.update(srccopinfo.modifies)
			#dstcopinfo.allocates.update(srccopinfo.allocates)

			# Reach for the function that the method call invokes.
			for c, f in srccopinfo.invokes:
				op = opThatInvokes(self.adb, f)
				invokes = self.adb.db.functionInfo(f).opInfo(op).context(c).invokes
				dstcopinfo.invokes.update(invokes)


		dstInfo.merge()

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
		return xform.allChildren(self, node)

def methodMeet(values):
	prototype = values[0]
	for value in values:
		if value != prototype:
			return dataflow.forward.top
	return prototype

def methodCall(console, extractor, adb):
	pattern = MethodPatternFinder()
	if not pattern.preprocess(extractor, adb):
		console.output("No method calls to fuse.")
		return

	db = adb.db


	numrewritten = 0
	for code, funcinfo in db.functionInfos.iteritems():
		analyze = MethodAnalysis(funcinfo, pattern)
		rewrite = MethodRewrite(adb, funcinfo, pattern)

		meet = methodMeet

		traverse = dataflow.forward.ForwardFlowTraverse(adb, meet, analyze, rewrite)
		t = dataflow.forward.MutateCode(traverse)

		# HACK
		analyze.flow = traverse.flow
		rewrite.flow = traverse.flow

		t(code)

		# HACK to turn attribute access assignments into discards.
		if rewrite.rewritten:
			optimization.simplify.simplify(extractor, analysis.analysisdatabase.DummyAnalysisDatabase(), code)

		if rewrite.rewritten:
			numrewritten += len(rewrite.rewritten)

	# TODO may not be entirely correct, as the method call may
	# not be fused in the final iteration.
	console.output("%d method calls fused." % numrewritten)
