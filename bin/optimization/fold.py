from util.typedispatch import *
from language.python import ast
from util import xform

from dataflow.forward import *

import language.python.fold as fold

from analysis import tools

from termrewrite import *

def floatMulRewrite(self, node):
	if not hasNumArgs(node, 2): return

	if isZero(node.args[0]):
		return node.args[0]
	elif isOne(node.args[0]):
		return node.args[1]
	elif isZero(node.args[1]):
		return node.args[1]
	elif isOne(node.args[1]):
		return node.args[0]

	# TODO negative 1 -> invert
	# Requires calling new code?

def floatAddRewrite(self, node):
	if not hasNumArgs(node, 2): return

	if isZero(node.args[0]):
		return node.args[1]
	elif isZero(node.args[1]):
		return node.args[0]

def convertToBoolRewrite(self, node):
	if not hasNumArgs(node, 1): return

	if isAnalysisInstance(node.args[0], bool):
		return node.args[0]

def makeCallRewrite(extractor):
	callRewrite = DirectCallRewriter(extractor)
	callRewrite.addRewrite('prim_float_mul', floatMulRewrite)
	callRewrite.addRewrite('prim_float_add', floatAddRewrite)
	callRewrite.addRewrite('convertToBool',  convertToBoolRewrite)
	return callRewrite


class FoldRewrite(object):
	__metaclass__ = typedispatcher

	def __init__(self, extractor, db, code):
		self.extractor = extractor
		self.db = db
		self.code = code

		self.created = set()

		self.callRewrite = makeCallRewrite(extractor)


	def logCreated(self, node):
		if isinstance(node, ast.Existing):
			self.created.add(node.object)

	@dispatch(ast.Existing)
	def visitExisting(self, node):
		return node

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


	def storeGraphForExistingObject(self, obj):
		sys = self.db.system

		slotName = sys.canonical.existingName(self.code, obj, None)
		slot = sys.roots.root(sys, slotName, sys.roots.regionHint)

		xtype = sys.canonical.existingType(obj)
		return slot.initializeType(sys, xtype)


	def getExistingNames(self, ref):
		if isinstance(ref, ast.Local):
			refs = ref.annotation.references
			if refs is not None:
				return [ref.xtype.obj for ref in refs[0]]
			else:
				return () # HACK?

		elif isinstance(ref, ast.Existing):
			return (ref.object,)

	def _cobjSlotRefs(self, cobj, slotType, key):
			fieldName = self.db.canonical.fieldName(slotType, key)
			slot = cobj.knownField(fieldName)
			return tuple(iter(slot))

	def getMethodFunction(self, expr, name):
		# Static setup
		canonical = self.db.canonical

		typeStrObj = self.extractor.getObject('type')
		dictStrObj = self.extractor.getObject('dictionary')


		# Dynamic setup
		funcs = set()
		exprObjs = self.getObjects(expr)
		nameObjs = self.getExistingNames(name)

		for exprObj in exprObjs:
			assert not isinstance(exprObj, tuple), exprObj
			typeObjs = self._cobjSlotRefs(exprObj, 'LowLevel', typeStrObj)
			for t in typeObjs:
				dictObjs = self._cobjSlotRefs(t, 'LowLevel', dictStrObj)
				for d in dictObjs:
					for nameObj in nameObjs:
						funcObjs = self._cobjSlotRefs(d, 'Dictionary', nameObj)
						funcs.update(funcObjs)

		if len(funcs) == 1:
			cobj = funcs.pop()
			result = self.existingFromNode(cobj)
			return result
		else:
			return None

	@dispatch(ast.MethodCall)
	def visitMethodCall(self, node):
		func = tools.singleCall(node)
		if func is not None:
			funcobj = self.getMethodFunction(node.expr, node.name)

			# TODO deal with single call / multiple function object case?
			if not funcobj: return node

			newargs = [node.expr]
			newargs.extend(node.args)
			result = ast.DirectCall(func, funcobj, newargs, node.kwds, node.vargs, node.kargs)
			result.annotation = node.annotation
			return self(result)
		return node

	def localToExisting(self, lcl, obj):
		node = ast.Existing(obj)
		node.annotation = lcl.annotation
		return node

	def existingFromNode(self, cobj):
		node = ast.Existing(cobj.xtype.obj)
		node.rewriteAnnotation(references=((cobj,), tuple([(cobj,) for context in self.code.annotation.contexts])))
		return node

	def existingFromObj(self, obj):
		if self.db:
			cobj = self.storeGraphForExistingObject(obj)
			node = self.existingFromNode(cobj)
			return node
		else:
			return ast.Existing(obj)


	@dispatch(ast.Local)
	def visitLocal(self, node):
		# Replace with query
		obj = tools.singleObject(node)
		if obj is not None:
			return self.localToExisting(node, obj)

		if hasattr(self, 'flow'):
			# Replace with dataflow
			const = self.flow.lookup(node)
			if const is not undefined:
				if isinstance(const, ast.Local):
					# Reach for the local definition
					return const
				elif const is not top:
					# Reach for the constant definition
					return self.existingFromObj(const)

		return node

	def annotateFolded(self, node):
		if isinstance(node, ast.Existing):
			node = self.existingFromObj(node.object)
		return node


	@dispatch(ast.BinaryOp)
	def visitBinaryOp(self, node):
		result = self.annotateFolded(fold.foldBinaryOpAST(self.extractor, node))
		self.logCreated(result)
		return result

	@dispatch(ast.UnaryPrefixOp)
	def visitUnaryPrefixOp(self, node):
		result = self.annotateFolded(fold.foldUnaryPrefixOpAST(self.extractor, node))
		self.logCreated(result)
		return result

	@dispatch(ast.ConvertToBool)
	def visitConvertToBool(self, node):
		result = self.annotateFolded(fold.foldBoolAST(self.extractor, node))
		self.logCreated(result)
		return result

	@dispatch(ast.Not)
	def visitNot(self, node):
		result = self.annotateFolded(fold.foldNotAST(self.extractor, node))
		self.logCreated(result)
		return result

	def tryDirectCallRewrite(self, node):
		result = self.callRewrite(self, node)
		if result is not None:
			self.logCreated(result)
			return self(result)
		return node

	@dispatch(ast.DirectCall)
	def visitDirectCall(self, node):
		if node.func is None:
			return node

		foldFunc = node.func.annotation.staticFold
		if foldFunc and not node.kwds and not node.vargs and not node.kargs:
			result = self.annotateFolded(fold.foldCallAST(self.extractor, node, foldFunc, node.args))
			if result is not node:
				self.logCreated(result)
				return result

		return self.tryDirectCallRewrite(node)

class FoldAnalysis(object):
	__metaclass__ = typedispatcher

	@dispatch(ast.Assign)
	def visitAssign(self, node):
		if len(node.lcls) == 1:
			lcl = node.lcls[0]
			if fold.existingConstant(node.expr):
				self.flow.define(lcl, node.expr.object)
				return node
			elif isinstance(node.expr, ast.Local):
				# Propagate names.
				if lcl.name and not node.expr.name:
					node.expr.name = lcl.name
				elif not lcl.name and node.expr.name:
					lcl.name = node.expr.name

				self.flow.define(lcl, node.expr)
				return node

		for lcl in node.lcls:
			self.flow.define(lcl, top)

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

	@dispatch(ast.CodeParameters)
	def visitCodeParameters(self, node):
		return node

	@dispatch(ast.Assign)
	def visitAssign(self, node):
		# Modified bottom up
		# Avoids folding assignment targets
		node = ast.Assign(self(node.expr), node.lcls)
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
	assert node.isAbstractCode(), type(node)

	if isinstance(node, ast.Code):
		analyze  = FoldAnalysis()
		rewrite  = FoldRewrite(extractor, db, node)
		rewriteS = FoldTraverse(rewrite, node)

		traverse = ForwardFlowTraverse(constMeet, analyze, rewriteS)
		t = MutateCode(traverse)

		# HACK
		analyze.flow = traverse.flow
		rewrite.flow = traverse.flow

		t(node)
	else:
		# HACK bypass dataflow analysis, as there's no real "flow"
		rewrite  = FoldRewrite(extractor, db, node)
		rewriteS = FoldTraverse(rewrite, node)
		xform.replaceAllChildren(rewriteS, node)


	existing = set(extractor.desc.objects)
	newobj = rewrite.created-existing

	for obj in newobj:
		extractor.desc.objects.append(obj)

	return node
