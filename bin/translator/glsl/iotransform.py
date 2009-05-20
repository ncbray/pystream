from util.typedispatch import *
from language.python import ast
from language.python import annotations

from optimization.dataflow import forward
from optimization.dataflow import reverse

import optimization.dce


from . import intrinsics

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
	def pathName(self, path):
		pathParts = [path[0].name]
		for part in path[1:]:
			attrParts = part[1].split('#')
			pathParts.append(attrParts[0])
		return "_".join(pathParts)

	def translate(self, path, target, frequency):
		if path not in self.shader.pathToLocal:
			lcl = ast.Local(self.pathName(path))
			lcl.annotation = target.annotation
			self.shader.pathToLocal[path] = lcl
			self.shader.localToPath[lcl] = path

			self.shader.frequency[lcl] = frequency
		else:
			# TODO check that the annotation is consistant?
			lcl = self.shader.pathToLocal[path]
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

		defn = self.flow.lookup(node.expr)
		if isPath(defn):
			assert isinstance(node.name, ast.Existing)
			name = node.name.object.pyobj
			newdefn = defn+((node.fieldtype, name),)
			freq = self.shader.frequency[self.shader.pathToLocal[defn]]

			lcl = self.translate(newdefn, targets[0], freq)
			self.flow.define(lcl, newdefn)
			return lcl
		else:
			return node


def transformInputs(shader):
	analyze = InputAnalysis()
	rewrite = InputTransform()

	traverse = forward.ForwardFlowTraverse(meet, analyze, rewrite)
	t = forward.MutateCode(traverse)

	# HACK
	analyze.flow = traverse.flow
	rewrite.flow = traverse.flow

	rewrite.shader = shader

	for arg in shader.code.parameters:
		path = (arg,)
		traverse.flow.define(arg, path)
		shader.pathToLocal[path] = arg
		shader.localToPath[arg] = path

	t(shader.code)


class OutputTransform(StrictTypeDispatcher):
	def __init__(self):
		self.returns = None

	def pathName(self, path):
		if isinstance(path[0], ast.Local):
			pathParts = [path[0].name]
		else:
			pathParts = [str(path[0])]

		for attrtype, name in path[1:]:
			if attrtype == 'Attribute':
				pathParts.append(name.split('#')[0])
			elif attrtype == 'Array':
				pathParts.append(str(name))
			elif attrtype == 'LowLevel':
				pathParts.append("LL" + str(name))
			else:
				assert False, (attrtype, name)

		return "_".join(pathParts)

	def translate(self, path, target, frequency):
		if path not in self.shader.pathToLocal:
			lcl = ast.Local(self.pathName(path))
			lcl.annotation = target.annotation
			self.shader.pathToLocal[path] = lcl
			self.shader.localToPath[lcl] = path

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
		defn = self.flow.lookup(node.expr)

		if isPath(defn):
			assert isinstance(node.name, ast.Existing)
			name = node.name.object.pyobj
			newdefn = defn+((node.fieldtype, name),)

			lcl = self.translate(newdefn, node.value, 'output')
			self.flow.define(lcl, newdefn)

			return self(ast.Assign(node.value,[lcl]))
		else:
			return node

	@dispatch(ast.Assign)
	def visitAssign(self, node):
		if isinstance(node.expr, ast.Local):
			assert len(node.lcls) == 1
			self.flow.define(node.expr, self.flow.lookup(node.lcls[0]))
		return node


	@dispatch(ast.Return)
	def visitReturn(self, node):
		if self.returns is None:
			self.returns = []
			for i, src in enumerate(node.exprs):
				newdefn = ('ret%d' % i,)

				lcl = self.translate(newdefn, src, 'output')
				self.flow.define(lcl, newdefn)

				self.returns.append(lcl)
		else:
			assert len(node.exprs) == len(self.returns)
			for lcl in self.returns:
				self.flow.define(lcl, (lcl,))

		assigns = [self(ast.Assign(src, [dst])) for src, dst in zip(node.exprs, self.returns)]
		#assigns.append(ast.Return(list(self.returns))) # HACK for DCE

		retop = ast.Return([])
		retop.annotation = node.annotation
		assigns.append(retop)
		return assigns

def transformOutputs(shader):
	rewrite = OutputTransform()

	traverse = reverse.ReverseFlowTraverse(meet, rewrite)
	t = reverse.MutateCode(traverse)

	# HACK
	rewrite.flow   = traverse.flow
	rewrite.shader = shader

	t(shader.code)

def hasIntrinsicType(extractor, lcl):
	for ref in lcl.annotation.references[0]:
		obj = ref.xtype.obj
		extractor.ensureLoaded(obj)
		assert hasattr(obj, 'type'), obj
		if obj.type.pyobj not in intrinsics.intrinsicTypes:
			return False
	return True

def evaluateShader(console, dataflow, shader):
	transformInputs(shader)
	transformOutputs(shader)

	# Kill orphans
	liveOut = set()
	for lcl, freq in shader.frequency.iteritems():
		if freq == 'output' and hasIntrinsicType(dataflow.extractor, lcl):
			liveOut.add(lcl)

	optimization.dce.dce(dataflow.extractor, shader.code, liveOut)