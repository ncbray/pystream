from util.typedispatch import *
from programIR.python import ast
from programIR import annotations

class ArgumentNormalizationAnalysis(object):
	__metaclass__ = typedispatcher

	def __init__(self, sys):
		self.sys = sys
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
	def visitCall(self, node):
		if self.applicable:
			self(node.selfarg)
			self(node.args)
			self(node.kwds)

			if node.kargs is self.vparam:
				self.applicable = False

	@defaultdispatch
	def visitDefault(self, node):
		if self.applicable:
			visitAllChildren(self, node)

	def process(self, node):
		if node.vparam:
			refs = node.vparam.annotation.references
			if refs is None: return False, 0

			lengths = set()
			for ref in refs[0]:
				length = ref.knownField(self.sys.lengthSlotName)
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
			self.vparam     = node.vparam
			self(node.ast)
			return self.applicable, vparamLen
		else:
			return False, 0


class ArgumentNormalizationTransform(object):
	__metaclass__ = typedispatcher

	def __init__(self, sys):
		self.sys = sys

	@defaultdispatch
	def visitDefault(self, node):
		return allChildren(self, node)

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
			return allChildren(self, node)

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
			return allChildren(self, node)

	@dispatch(ast.DirectCall)
	def visitDirectCall(self, node):
		if node.vargs is self.vparam:
			selfarg = self(node.selfarg)
			args    = self.extend(self(node.args), self.newParams)
			kwds    = self(node.kwds)
			kargs   = self(node.kargs)
			result = ast.DirectCall(node.func, selfarg, args, kwds, None, kargs)

			result.annotation = node.annotation
			return result

		else:
			return allChildren(self, node)

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

		self.code   = node
		self.vparam = node.vparam

		self.newParams = [ast.Local() for i in range(vparamLen)]
		self.newNames  = [None for i in range(vparamLen)]

		for i, lcl in enumerate(self.newParams):
			field = self.sys.canonical.fieldName('Array', self.sys.extractor.getObject(i))
			self.transferReferences(self.vparam, field, lcl)

		node.parameters = self.extend(node.parameters, self.newParams)
		node.parameternames = self.extend(node.parameternames, self.newNames)
		node.vparam = None

		node.ast = self(node.ast)

def normalizeArguments(dataflow, db):
	analysis  = ArgumentNormalizationAnalysis(dataflow)
	transform = ArgumentNormalizationTransform(dataflow)

	for code in db.liveFunctions():
		applicable, vparamLen = analysis.process(code)
		if applicable:
			transform.process(code, vparamLen)