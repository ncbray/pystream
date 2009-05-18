from util.typedispatch import *
from language.python import ast
from language.python import annotations

from optimization.dataflow import forward

import optimization.simplify


def isPath(defn):
	return defn is not forward.undefined and defn is not forward.top

class IOAnalysis(StrictTypeDispatcher):
	def clearTargets(self, targets):
		for lcl in targets:
			self.flow.define(lcl, forward.top)

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

class IOTransform(StrictTypeDispatcher):
	def pathName(self, path):
		pathParts = [path[0].name]
		for part in path[1:]:
			print part
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

#			print "XFORM", freq, node.expr
#			print node
#			print newdefn

			lcl = self.translate(newdefn, targets[0], freq)
			self.flow.define(lcl, newdefn)
			return lcl
		else:
			return node

def meet(values):
	prototype = values[0]
	for value in values:
		if value != prototype:
			return dataflow.forward.top
	return prototype

def evaluateShader(console, dataflow, shader):
	analyze = IOAnalysis()
	rewrite = IOTransform()

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

	# Kill orphans
	optimization.simplify.simplify(dataflow.extractor, dataflow.db, shader.code)