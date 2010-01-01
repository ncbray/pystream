from util.typedispatch import *
from language.python import ast
from language.python import annotations

class ArgumentNormalizationAnalysis(TypeDispatcher):
	def __init__(self, storeGraph):
		TypeDispatcher.__init__(self)
		self.storeGraph = storeGraph
		self.applicable = True
		self.vparam = None

	@dispatch(ast.Local)
	def visitLocal(self, node):
		if node is self.vparam:
			self.applicable = False

	@dispatch(ast.Call, ast.MethodCall)
	def visitCall(self, node):
		if self.applicable:
			self(node.expr)
			self(node.args)
			self(node.kwds)

			if node.kargs is self.vparam:
				self.applicable = False

	@dispatch(ast.DirectCall)
	def visitDirectCall(self, node):
		if self.applicable:
			self(node.selfarg)
			self(node.args)
			self(node.kwds)

			if node.kargs is self.vparam:
				self.applicable = False

	@dispatch(list, tuple)
	def visitContainer(self, node):
		for child in node:
			self(child)

	@dispatch(ast.leafTypes, ast.Existing)
	def visitLeaf(self, node):
		pass

	@defaultdispatch
	def visitDefault(self, node):
		if self.applicable:
			node.visitChildren(self)

	def process(self, node):
		if not node.isStandardCode():
			return False, 0

		if node.annotation.descriptive:
			return False, 0

		p = node.codeparameters
		if p.vparam:
			refs = p.vparam.annotation.references
			if refs is None: return False, 0

			lengths = set()
			for ref in refs[0]:
				length = ref.knownField(self.storeGraph.lengthSlotName)
				for obj in length:
					obj = obj.xtype
					if not obj.isExisting(): return False, 0
					obj = obj.obj
					if not obj.isConstant(): return False, 0
					lengths.add(obj.pyobj)

			# We don't "partially" optimize variable length vparams
			# as this would require rewriting the heap.
			if len(lengths) != 1:
				return False, 0

			vparamLen = lengths.pop()

			self.applicable = True
			self.vparam     = p.vparam
			self(node.ast)
			return self.applicable, vparamLen
		else:
			return False, 0


class ArgumentNormalizationTransform(TypeDispatcher):
	def __init__(self, storeGraph):
		self.storeGraph = storeGraph

	@defaultdispatch
	def visitDefault(self, node):
		return node.rewriteChildren(self)

	@dispatch(list, tuple)
	def visitContainer(self, node):
		return [self(child) for child in node]

	@dispatch(ast.leafTypes)
	def visitLeaf(self, node):
		return node

	@dispatch(ast.Call)
	def visitCall(self, node):
		if node.vargs is self.vparam:
			expr    = self(node.expr)
			args    = self.extend(self(node.args), self.newParams)
			kwds    = self(node.kwds)
			kargs   = self(node.kargs)
			result = ast.Call(expr, args, kwds, None, kargs)

			result.annotation = node.annotation
			return result
		else:
			return node.rewriteChildren(self)

	@dispatch(ast.MethodCall)
	def visitMethodCall(self, node):
		if node.vargs is self.vparam:
			expr    = self(node.expr)
			args    = self.extend(self(node.args), self.newParams)
			kwds    = self(node.kwds)
			kargs   = self(node.kargs)
			result = ast.MethodCall(expr, node.name, args, kwds, None, kargs)

			result.annotation = node.annotation
			return result
		else:
			return node.rewriteChildren(self)

	@dispatch(ast.DirectCall)
	def visitDirectCall(self, node):
		if node.vargs is self.vparam:
			selfarg = self(node.selfarg)
			args    = self.extend(self(node.args), self.newParams)
			kwds    = self(node.kwds)
			kargs   = self(node.kargs)
			result = ast.DirectCall(node.code, selfarg, args, kwds, None, kargs)

			result.annotation = node.annotation
			return result

		else:
			return node.rewriteChildren(self)

	def extend(self, old, new):
		return list(old)+new

	# Generic heap.field -> local transfer
	# TODO refactor into library?
	def transferReferences(self, src, field, dst):
		refs = src.annotation.references
		cout = []
		for cindex, context in enumerate(self.code.annotation.contexts):
			values = set()
			for ref in refs[1][cindex]: values.update(ref.knownField(field))
			cout.append(annotations.annotationSet(values))

		refs = annotations.makeContextualAnnotation(cout)
		dst.rewriteAnnotation(references=refs)


	def process(self, node, vparamLen):
		# TODO rewrite local references.

		p = node.codeparameters

		self.code   = node
		self.vparam = p.vparam

		self.newParams = [ast.Local(None) for i in range(vparamLen)]
		self.newNames  = [None for i in range(vparamLen)]

		if vparamLen > 0:
			# Defaults are never used
			defaults = ()
		else:
			# Number of arguments unchanged, defaults may be used, do nothing
			defaults = p.defaults

		for i, lcl in enumerate(self.newParams):
			field = self.storeGraph.canonical.fieldName('Array', self.storeGraph.extractor.getObject(i))
			self.transferReferences(self.vparam, field, lcl)

		selfparam = p.selfparam
		parameters = self.extend(p.params, self.newParams)
		parameternames = self.extend(p.paramnames, self.newNames)
		vparam = None
		kparam = p.kparam
		returnparams = p.returnparams

		node.codeparameters = ast.CodeParameters(selfparam, parameters, parameternames, defaults, vparam, kparam, returnparams)
		node.ast = self(node.ast)

def evaluate(compiler):
	with compiler.console.scope('argument normalization'):
		analysis  = ArgumentNormalizationAnalysis(compiler.storeGraph)
		transform = ArgumentNormalizationTransform(compiler.storeGraph)

		for code in compiler.liveCode:
			applicable, vparamLen = analysis.process(code)
			if applicable:
				transform.process(code, vparamLen)
