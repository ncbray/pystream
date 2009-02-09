from util.typedispatch import *
from programIR.python import ast
from util import xform

from dataflow.forward import *

import programIR.python.fold as fold


class FoldRewrite(object):
	__metaclass__ = typedispatcher

	def __init__(self, extractor, adb, code):
		self.extractor = extractor
		self.adb = adb
		self.code = code

		self.constLUT = DynamicDict()

		self.created = set()

	def logCreated(self, node):
		if isinstance(node, ast.Existing):
			self.created.add(node.object)

	@dispatch(ast.Call)
	def visitCall(self, node):
		func = self.adb.singleCall(self.code, node)
		if func is not None:
			result = ast.DirectCall(func, node.expr, node.args, node.kwds, node.vargs, node.kargs)
			self.adb.trackRewrite(self.code, node, result)
			return result

		return node

	def getObjects(self, ref):
		if isinstance(ref, ast.Local):
			return self.adb.db.functionInfo(self.code).localInfo(ref).merged.references
		elif isinstance(ref, ast.Existing):
			# HACK creating a de-contextualized existing object?  This should really be a "global" object...
			obj = ref.object
			sys = self.adb.db.system
			existingName = sys.canonical.existingName(self.code, obj, None)
			slot = sys.roots.root(sys, existingName, sys.roots.regionHint)
			slot.initializeType(sys, sys.canonical.existingType(obj))

			objs = tuple(iter(slot))
			return objs
		else:
			assert False, type(ref)



	def getExistingNames(self, ref):
		if isinstance(ref, ast.Local):
			refs = self.adb.db.functionInfo(self.code).localInfo(ref).merged.references
			return [ref.xtype.obj for ref in refs]
		elif isinstance(ref, ast.Existing):
			return (ref.object,)

	def getMethodFunction(self, expr, name):
		# Static setup
		db = self.adb.db
		typeStrObj = self.extractor.getObject('type')
		dictStrObj = self.extractor.getObject('dictionary')

		def cobjSlotRefs(cobj, slotType, key):
			fieldName = db.canonical.fieldName(slotType, key)
			slot = cobj.knownField(fieldName)
			return tuple(iter(slot))

		# Dynamic setup
		funcs = set()
		exprObjs = self.getObjects(expr)
		nameObjs = self.getExistingNames(name)

		for exprObj in exprObjs:
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
		func = self.adb.singleCall(self.code, node)
		if func is not None:
			funcobj = self.getMethodFunction(node.expr, node.name)

			# TODO deal with single call / multiple function object case?
			if not funcobj:
				return node

			newargs = [node.expr]
			newargs.extend(node.args)
			result = ast.DirectCall(func, funcobj, newargs, node.kwds, node.vargs, node.kargs)
			self.adb.trackRewrite(self.code, node, result)
			return result
		return node

	@dispatch(ast.Local)
	def visitLocal(self, node):
		# Replace with query
		obj = self.adb.singleObject(self.code, node)
		if obj is not None:
			replace = ast.Existing(obj)
			return replace

		# Replace with dataflow
		const = self.flow.lookup(node)
		if const is not undefined and const is not top:
			return ast.Existing(const)

		return node

	@dispatch(ast.BinaryOp)
	def visitBinaryOp(self, node):
		result = fold.foldBinaryOpAST(self.extractor, node)
		#self.adb.trackRewrite(node, result)
		self.logCreated(result)
		return result

	@dispatch(ast.UnaryPrefixOp)
	def visitUnaryPrefixOp(self, node):
		result = fold.foldUnaryPrefixOpAST(self.extractor, node)
		#self.adb.trackRewrite(node, result)
		self.logCreated(result)
		return result

	@dispatch(ast.ConvertToBool)
	def visitConvertToBool(self, node):
		result = fold.foldBoolAST(self.extractor, node)
		#self.adb.trackRewrite(node, result)
		self.logCreated(result)
		return result

	@dispatch(ast.Not)
	def visitNot(self, node):
		result = fold.foldNotAST(self.extractor, node)
		#self.adb.trackRewrite(node, result)
		self.logCreated(result)
		return result


class FoldAnalysis(object):
	__metaclass__ = typedispatcher

	@dispatch(ast.Assign)
	def visitAssign(self, node):
		if fold.existingConstant(node.expr):
			self.flow.define(node.lcl, node.expr.object)
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

	def __init__(self, adb, strategy, function):
		self.adb      = adb
		self.strategy = strategy
		self.code = function

	@defaultdispatch
	def default(self, node):
		# Bottom up
		nodeT = xform.allChildren(self, node)
		self.adb.trackRewrite(self.code, node, nodeT)
		result = self.strategy(nodeT)
		return result

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

def foldConstants(extractor, adb, node):
	assert isinstance(node, ast.Code), type(node)

	analyze = FoldAnalysis()
	rewrite = FoldRewrite(extractor, adb, node)
	rewriteS = FoldTraverse(adb, rewrite, node)

	traverse = ForwardFlowTraverse(adb, constMeet, analyze, rewriteS)
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
