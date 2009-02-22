from util.typedispatch import *
from programIR.python import ast
from util import xform

from dataflow.forward import *

import programIR.python.fold as fold

from analysis import tools

class FoldRewrite(object):
	__metaclass__ = typedispatcher

	def __init__(self, extractor, db, code):
		self.extractor = extractor
		self.db = db
		self.code = code

		self.constLUT = DynamicDict()

		self.created = set()

	def logCreated(self, node):
		if isinstance(node, ast.Existing):
			self.created.add(node.object)

	@dispatch(ast.Call)
	def visitCall(self, node):
		func = tools.singleCall(node)
		if func is not None:
			result = ast.DirectCall(func, node.expr, node.args, node.kwds, node.vargs, node.kargs)
			result.annotation = node.annotation
			return self(result)

		return node

	def getObjects(self, ref):
		if isinstance(ref, ast.Local):
			refs = ref.annotation.references
			if refs is not None:
				return refs[0]
			else:
				return () # HACK?
		elif isinstance(ref, ast.Existing):
			# May happen durring decompilation.
			if self.db is None:
				return ()

			# HACK creating a de-contextualized existing object?  This should really be a "global" object...
			obj = ref.object
			sys = self.db.system
			existingName = sys.canonical.existingName(self.code, obj, None)
			slot = sys.roots.root(sys, existingName, sys.roots.regionHint)
			slot.initializeType(sys, sys.canonical.existingType(obj))

			objs = tuple(iter(slot))
			return objs
		else:
			assert False, type(ref)



	def getExistingNames(self, ref):
		if isinstance(ref, ast.Local):
			refs = ref.annotation.references
			if refs is not None:
				return [ref.xtype.obj for ref in refs[0]]
			else:
				return () # HACK?

		elif isinstance(ref, ast.Existing):
			return (ref.object,)

	def getMethodFunction(self, expr, name):
		# Static setup
		canonical = self.db.canonical

		typeStrObj = self.extractor.getObject('type')
		dictStrObj = self.extractor.getObject('dictionary')

		def cobjSlotRefs(cobj, slotType, key):
			fieldName = canonical.fieldName(slotType, key)
			slot = cobj.knownField(fieldName)
			return tuple(iter(slot))

		# Dynamic setup
		funcs = set()
		exprObjs = self.getObjects(expr)
		nameObjs = self.getExistingNames(name)

		for exprObj in exprObjs:
			assert not isinstance(exprObj, tuple), exprObj
			typeObjs = cobjSlotRefs(exprObj, 'LowLevel', typeStrObj)
			for t in typeObjs:
				dictObjs = cobjSlotRefs(t, 'LowLevel', dictStrObj)
				for d in dictObjs:
					for nameObj in nameObjs:
						funcObjs = cobjSlotRefs(d, 'Dictionary', nameObj)
						funcs.update(funcObjs)

		if len(funcs) == 1:
			return ast.Existing(funcs.pop().xtype.obj)
		else:
			return None

	@dispatch(ast.MethodCall)
	def visitMethodCall(self, node):
		func = tools.singleCall(node)
		if func is not None:
			funcobj = self.getMethodFunction(node.expr, node.name)

			# TODO deal with single call / multiple function object case?
			if not funcobj:
				return node

			newargs = [node.expr]
			newargs.extend(node.args)
			result = ast.DirectCall(func, funcobj, newargs, node.kwds, node.vargs, node.kargs)
			result.annotation = node.annotation
			return self(result)
		return node

	@dispatch(ast.Local)
	def visitLocal(self, node):
		# Replace with query
		obj = tools.singleObject(node)
		if obj is not None:
			replace = ast.Existing(obj)
			return replace

		# Replace with dataflow
		const = self.flow.lookup(node)
		if const is not undefined:
			if isinstance(const, ast.Local):
				# Reach for the local definition
				return const
			elif const is not top:
				# Reach for the constant definition
				return ast.Existing(const)

		return node

	@dispatch(ast.BinaryOp)
	def visitBinaryOp(self, node):
		result = fold.foldBinaryOpAST(self.extractor, node)
		self.logCreated(result)
		return result

	@dispatch(ast.UnaryPrefixOp)
	def visitUnaryPrefixOp(self, node):
		result = fold.foldUnaryPrefixOpAST(self.extractor, node)
		self.logCreated(result)
		return result

	@dispatch(ast.ConvertToBool)
	def visitConvertToBool(self, node):
		result = fold.foldBoolAST(self.extractor, node)
		self.logCreated(result)
		return result

	@dispatch(ast.Not)
	def visitNot(self, node):
		result = fold.foldNotAST(self.extractor, node)
		self.logCreated(result)
		return result

	@dispatch(ast.DirectCall)
	def visitDirectCall(self, node):
		foldFunc = node.func.annotation.staticFold
		if foldFunc and not node.kwds and not node.vargs and not node.kargs:
			result = fold.foldCallAST(self.extractor, node, foldFunc, node.args)

#			print "?", node
#			print foldFunc
#			print result
#			print

			self.logCreated(result)
			return result
		return node

class FoldAnalysis(object):
	__metaclass__ = typedispatcher

	@dispatch(ast.Assign)
	def visitAssign(self, node):
		if fold.existingConstant(node.expr):
			self.flow.define(node.lcl, node.expr.object)
		elif isinstance(node.expr, ast.Local):
			# Propagate names.
			if node.lcl.name and not node.expr.name:
				node.expr.name = node.lcl.name
			elif not node.lcl.name and node.expr.name:
				node.lcl.name = node.expr.name

			self.flow.define(node.lcl, node.expr)
		else:
			self.flow.define(node.lcl, top)
		return node

	@dispatch(ast.Delete)
	def visitDelete(self, node):
		self.flow.undefine(node.lcl)
		return node



# Restricted traversal, so not all locals are rewritten.
class FoldTraverse(object):
	__metaclass__ = typedispatcher

	def __init__(self, strategy, function):
		self.strategy = strategy
		self.code = function

	@defaultdispatch
	def default(self, node):
		# Bottom up
		return self.strategy(allChildren(self, node))

	@dispatch(ast.Assign)
	def visitAssign(self, node):
		# Modified bottom up
		# Avoids folding assignment targets
		node = ast.Assign(self(node.expr), node.lcl)
		node = self.strategy(node)
		return node

	@dispatch(ast.Delete)
	def visitDelete(self, node):
		# Avoids folding delete targets
		node = self.strategy(node)
		return node

def constMeet(values):
	prototype = values[0]
	for value in values[1:]:
		if value != prototype:
			return top
	return prototype

def foldConstants(extractor, db, node):
	assert isinstance(node, ast.Code), type(node)

	analyze  = FoldAnalysis()
	rewrite  = FoldRewrite(extractor, db, node)
	rewriteS = FoldTraverse(rewrite, node)

	traverse = ForwardFlowTraverse(constMeet, analyze, rewriteS)
	t = MutateCode(traverse)

	# HACK
	analyze.flow = traverse.flow
	rewrite.flow = traverse.flow

	t(node)

	existing = set(extractor.desc.objects)
	newobj = rewrite.created-existing

	for obj in newobj:
		extractor.desc.objects.append(obj)

	return node
