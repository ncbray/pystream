# Copyright 2011 Nicholas Bray
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from util.typedispatch import *
from language.python import ast

from dataflow.reverse import *

from analysis import tools

def liveMeet(values):
	if values:
		return top
	else:
		return undefined

# Mark a locals in an AST subtree as used.
class MarkLocals(TypeDispatcher):
	@dispatch(ast.leafTypes)
	def visitLeaf(self, node):
		pass

	@dispatch(ast.Local)
	def visitLocal(self, node):
		self.flow.define(node, top)

	@dispatch(ast.GetGlobal, ast.SetGlobal)
	def visitGlobalOp(self, node):
		self.flow.define(self.selfparam, top)
		node.visitChildren(self)

	@defaultdispatch
	def default(self, node):
		node.visitChildren(self)


nodesWithNoSideEffects = (ast.GetGlobal, ast.Existing, ast.Local,
						ast.Is, ast.Load, ast.Allocate,
						ast.BuildTuple, ast.BuildList, ast.BuildMap)

class MarkLive(TypeDispatcher):
	def __init__(self, code):
		self.code   = code
		self.marker = MarkLocals()

	def hasNoSideEffects(self, node):
		if self.descriptive():
			return isinstance(node, (ast.Local, ast.Existing))
		else:
			return isinstance(node, nodesWithNoSideEffects) or not tools.mightHaveSideEffect(node)

	def descriptive(self):
		return self.code.annotation.descriptive

	@dispatch(ast.Condition)
	def visitCondition(self, node):
		self.marker(node.conditional)
		return node

	@dispatch(ast.Discard)
	def visitDiscard(self, node):
		if self.hasNoSideEffects(node.expr):
			return []
		else:
			self.marker(node)
			return node

	@dispatch(ast.Assign)
	def visitAssign(self, node):
		used = any([self.flow.lookup(lcl) is not undefined for lcl in node.lcls])
		if used:
			for lcl in node.lcls:
				self.flow.undefine(lcl)
			self.marker(node.expr)
			return node

		elif self.hasNoSideEffects(node.expr):
			return []
		else:
			node = ast.Discard(node.expr)
			node = self(node)
			return node

	@dispatch(ast.Delete)
	def visitDelete(self, node):
		self.flow.undefine(node.lcl)

	@defaultdispatch
	def default(self, node):
		if isinstance(node, ast.SimpleStatement):
			self.marker(node)
		return node

	@dispatch(ast.InputBlock)
	def visitInputBlock(self, node):
		inputs = []
		for input in node.inputs:
			if self.flow.lookup(input.lcl) is not undefined:
				inputs.append(input)
		return ast.InputBlock(inputs)

	@dispatch(ast.OutputBlock)
	def visitOutputBlock(self, node):
		for output in node.outputs:
			self.flow.define(output.expr, top)
		return node

	@dispatch(ast.Return)
	def visitReturn(self, node):
		for lcl in self.initialLive:
			self.flow.define(lcl, top)
		self.marker(node)
		return node

	def filterParam(self, p):
		if p is None:
			return None
		elif self.flow.lookup(p) is undefined:
			return ast.DoNotCare()
		else:
			return p

	@dispatch(ast.CodeParameters)
	def visitCodeParameters(self, node):
		# Insert don't care for unused parameters.
		# selfparam is a special case, it's OK if it disappears in descriptive stubs.
		selfparam = self.filterParam(node.selfparam)

		if self.descriptive():
			params = node.params
			vparam = node.vparam
			kparam = node.kparam
		else:
			params = [self.filterParam(p) for p in node.params]
			vparam = self.filterParam(node.vparam)
			kparam = self.filterParam(node.kparam)

		return ast.CodeParameters(selfparam, params, node.paramnames, node.defaults, vparam, kparam, node.returnparams)

def evaluateCode(compiler, node, initialLive=None):
	rewrite = MarkLive(node)
	traverse = ReverseFlowTraverse(liveMeet, rewrite)

	# HACK
	rewrite.flow = traverse.flow
	rewrite.marker.flow = traverse.flow
	rewrite.marker.selfparam = node.codeparameters.selfparam

	t = MutateCodeReversed(traverse)

	# For shader translation, locals may be used as outputs.
	# We need to retain these locals.
	rewrite.initialLive = initialLive if initialLive != None else ()

	result = t(node)

	return result
