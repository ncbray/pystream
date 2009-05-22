from util.typedispatch import *
from language.python import ast
from language.python import annotations

from optimization.dataflow import forward
from optimization.dataflow import reverse

import optimization.dce


from . import intrinsics

def hasIntrinsicType(extractor, lcl):
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
	def translate(self, path, target, frequency):
		if path not in self.shader.pathToLocal:
			lcl = ast.Local(path.fullName())
			lcl.annotation = target.annotation

			self.shader.bindPath(path, lcl)

			self.shader.frequency[lcl] = frequency
		else:
			# TODO check that the annotation is consistant?
			lcl = path.local
		return lcl

	@defaultdispatch
	def visit(self, node, targets=None):
		return allChildren(self, node)

	@dispatch(ast.Assign)
	def visitAssign(self, node):
		return ast.Assign(self(node.expr, node.lcls), self(node.lcls))


	@dispatch(ast.Load)
	def visitLoad(self, node, targets):
		if len(targets) != 1: return node

		if hasIntrinsicType(self.extractor, node.expr): return node

		defn = self.flow.lookup(node.expr)
		if isPath(defn):
			freq = self.shader.frequency[defn.local]

			newdefn = defn.extend(node)
			lcl = self.translate(newdefn, targets[0], freq)

			self.flow.define(newdefn.local, newdefn)
			return newdefn.local
		else:
			return node


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
	freqs = ['uniform']+['input']*(len(shader.code.parameters)-1)
	for arg, freq in zip(shader.code.parameters, freqs):
		defn = shader.getRoot(arg.name, arg)
		lcl = defn.local
		shader.frequency[lcl] = freq
		traverse.flow.define(arg, defn)

	t(shader.code)


class OutputTransform(StrictTypeDispatcher):
	def __init__(self):
		self.returns = None

	def translate(self, path, target, frequency):
		if path not in self.shader.pathToLocal:
			lcl = ast.Local(path.fullName())
			lcl.annotation = target.annotation

			self.shader.bindPath(path, lcl)
			self.shader.frequency[lcl] = frequency
		else:
			# TODO check that the annotation is consistant?
			lcl = self.shader.pathToLocal[path]
		return lcl

	@defaultdispatch
	def visit(self, node, targets=None):
		return allChildren(self, node)

	@dispatch(ast.Store)
	def visitStore(self, node):
		if hasIntrinsicType(self.extractor, node.expr): return node

		defn = self.flow.lookup(node.expr)

		if isPath(defn):
			freq = 'output'

			newdefn = defn.extend(node)
			lcl = self.translate(newdefn, node.value, freq)

			self.flow.define(newdefn.local, newdefn)
			return self(ast.Assign(node.value, [newdefn.local]))
		else:
			return node

	@dispatch(ast.Assign)
	def visitAssign(self, node):
		if isinstance(node.expr, ast.Local):
			assert len(node.lcls) == 1
			self.flow.define(node.expr, self.flow.lookup(node.lcls[0]))
		return node


	def initReturns(self):
		self.returns = []
		for i, src in enumerate(self.shader.code.returnparams):
			name = 'ret%d' % i

			newdefn = self.shader.getRoot(name, src)
			lcl = newdefn.local

			self.shader.frequency[lcl] = 'output'
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

def transformOutputs(extractor, shader):
	rewrite = OutputTransform()

	traverse = reverse.ReverseFlowTraverse(meet, rewrite)
	t = reverse.MutateCode(traverse)

	# HACK
	rewrite.flow   = traverse.flow
	rewrite.shader = shader
	rewrite.extractor = extractor

	t(shader.code)

def evaluateShader(console, dataflow, shader):
	transformInputs(dataflow.extractor, shader)
	transformOutputs(dataflow.extractor, shader)

	# Kill orphans
	liveOut = set()
	for lcl, freq in shader.frequency.iteritems():
		if freq == 'output' and hasIntrinsicType(dataflow.extractor, lcl):
			liveOut.add(lcl)

	optimization.dce.dce(dataflow.extractor, shader.code, liveOut)