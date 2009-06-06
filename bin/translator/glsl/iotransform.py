from util.typedispatch import *
from language.python import ast
from language.python import annotations

from optimization.dataflow import forward
from optimization.dataflow import reverse

import optimization.dce


from . import intrinsics

def hasIntrinsicType(extractor, lcl):
	if lcl.annotation.references is None:
		return False

	for ref in lcl.annotation.references[0]:
		obj = ref.xtype.obj
		extractor.ensureLoaded(obj)
		assert hasattr(obj, 'type'), obj
		if obj.type.pyobj not in intrinsics.intrinsicTypes:
			return False
	return True

def isPath(defn):
	return defn is not forward.undefined and defn is not forward.top

def meet(values):
	prototype = values[0]
	for value in values:
		if value != prototype:
			return dataflow.forward.top
	return prototype


class InputAnalysis(StrictTypeDispatcher):
	def clearTargets(self, targets):
		for lcl in targets:
			self.flow.define(lcl, forward.top)

	@dispatch(ast.Store)
	def visitStore(self, node):
		pass

	@dispatch(ast.Assign)
	def visitAssign(self, node):
		if isinstance(node.expr, ast.Local):
			assert len(node.lcls) == 1
			self.flow.define(node.lcls[0], self.flow.lookup(node.expr))
		else:
			self.clearTargets(node.lcls)

	@dispatch(ast.Return)
	def visitReturn(self, node):
		pass # TODO paths for return values?

class InputTransform(StrictTypeDispatcher):
	@dispatch(ast.Local)
	def visitLocal(self, node, targets=None):
		defn = self.flow.lookup(node)
		if isPath(defn):
			return defn.local
		else:
			return node

	@defaultdispatch
	def visit(self, node, targets=None):
		return allChildren(self, node)

	@dispatch(ast.Assign)
	def visitAssign(self, node):
		return ast.Assign(self(node.expr, node.lcls), self(node.lcls))


	@dispatch(ast.Load)
	def visitLoad(self, node, targets):
		defn = self.flow.lookup(node.expr)
		if isPath(defn) and not hasIntrinsicType(self.extractor, node.expr) and len(targets) == 1:
			newdefn = self.shader.extend(defn, node, targets[0], defn.frequency)
			self.flow.define(newdefn.local, newdefn)
			return newdefn.local
		else:
			return allChildren(self, node)


def transformInputs(extractor, shader):
	analyze = InputAnalysis()
	rewrite = InputTransform()

	traverse = forward.ForwardFlowTraverse(meet, analyze, rewrite)
	t = forward.MutateCode(traverse)

	# HACK
	analyze.flow = traverse.flow
	rewrite.flow = traverse.flow

	rewrite.shader = shader
	rewrite.extractor = extractor

	# HACK first parameter as uniform
	freqs = ['uniform']+['input']*(len(shader.code.params)-1)
	for arg, freq in zip(shader.code.params, freqs):
		defn = shader.getRoot(arg.name, arg, freq)
		traverse.flow.define(arg, defn)

	t(shader.code)


class OutputTransform(StrictTypeDispatcher):
	def __init__(self):
		self.returns = None

	@defaultdispatch
	def visit(self, node, targets=None):
		return allChildren(self, node)

	@dispatch(ast.Store)
	def visitStore(self, node):
		defn = self.flow.lookup(node.expr)
		if isPath(defn) and not hasIntrinsicType(self.context.extractor, node.expr):
			newdefn = self.shader.extend(defn, node, node.value, 'output')
			self.flow.define(newdefn.local, newdefn)
			return self(ast.Assign(node.value, [newdefn.local]))
		else:
			return allChildren(self, node)

	@dispatch(ast.Assign)
	def visitAssign(self, node):
		if isinstance(node.expr, ast.Local):
			assert len(node.lcls) == 1
			self.flow.define(node.expr, self.flow.lookup(node.lcls[0]))
		return node


	def initReturns(self):
		self.returns = []
		for i, src in enumerate(self.shader.code.returnparams):
			newdefn = self.shader.getRoot('ret%d' % i, src, 'output')

			lcl = newdefn.local
			self.returns.append(lcl)
			self.flow.define(lcl, newdefn)

	@dispatch(ast.Return)
	def visitReturn(self, node):
		self.initReturns()

		# Transform the return into assignments to outputs.
		assert len(node.exprs) == len(self.returns)
		assigns = [self(ast.Assign(src, [dst])) for src, dst in zip(node.exprs, self.returns)]

		# Eliminating the return might change sematics, so create
		# an empty return.
		retop = ast.Return([])
		retop.annotation = node.annotation
		assigns.append(retop)

		return assigns

def transformOutputs(context, shader, pathMatcher):
	rewrite = OutputTransform()

	traverse = reverse.ReverseFlowTraverse(meet, rewrite)
	t = reverse.MutateCode(traverse)

	# HACK
	rewrite.flow        = traverse.flow
	rewrite.context     = context
	rewrite.shader      = shader
	rewrite.pathMatcher = pathMatcher

	t(shader.code)


def getOutputs(extractor, shader):
	liveOut = set()
	for path in shader.pathToLocal.iterkeys():
		if path.frequency == 'output' and hasIntrinsicType(extractor, path.local):
			liveOut.add(path.local)
	return liveOut

def evaluateShader(context, shader, pathMatcher):
	transformInputs(context.extractor, shader)
	transformOutputs(context, shader, pathMatcher)

	# Kill orphans
	optimization.dce.dce(context.extractor, shader.code, getOutputs(context.extractor, shader))