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
from . import graph as cfg
from . dfs import CFGDFS

from . import dom

class CollectModifies(TypeDispatcher):
	def __init__(self):
		self.mod = {}
		self.order = []

	def modified(self, node):
		assert isinstance(node, ast.Local)
		self._modified(node, self.current)

	def _modified(self, node, block):
		if not node in self.mod:
			self.mod[node] = set()

		# .data is the djnode
		self.mod[node].add(block.data)

	@dispatch(cfg.Entry, cfg.Exit, cfg.Merge, cfg.Yield, cfg.Switch)
	def visitLeaf(self, node):
		self.order.append(node)

	@dispatch(cfg.TypeSwitch)
	def visitTypeSwitch(self, node):
		self.order.append(node)

		for i, case in enumerate(node.original.cases):
			if case.expr:
				self._modified(case.expr, node.getExit(i))


	@dispatch(ast.Discard, ast.Return, ast.SetAttr, ast.Store, ast.OutputBlock)
	def visitDiscard(self, node):
		pass

	@dispatch(ast.InputBlock)
	def visitInputBlock(self, node):
		for input in node.inputs:
			self.modified(input.lcl)

	@dispatch(ast.Assign)
	def visitAssign(self, node):
		for target in node.lcls:
			self.modified(target)

	@dispatch(ast.UnpackSequence)
	def visitUnpackSequence(self, node):
		for target in node.targets:
			self.modified(target)

	@dispatch(cfg.Suite)
	def visitSuite(self, node):
		self.order.append(node)
		self.current = node
		for op in node.ops:
			self(op)
		self.current = None

class SSARename(TypeDispatcher):
	def __init__(self, g, rename, merge):
		self.g = g
		self.rename = rename
		self.merge  = merge

		self.frames = {}
		self.currentFrame = None

		self.read = set()

		self.fixup = []

	def clone(self, lcl, frame):
		if lcl:
			result = lcl.clone()
			frame[lcl] = result
			return result
		else:
			return None

	@dispatch(cfg.Entry)
	def visitCFGEntry(self, node):
		frame = {}

		cparam = self.g.code.codeparameters

		# Set the parameters

		selfparam = self.clone(cparam.selfparam, frame)
		params = [self.clone(p, frame) for p in cparam.params]
		vparam = self.clone(cparam.vparam, frame)
		kparam = self.clone(cparam.kparam, frame)

		# Construct the parameters
		self.g.code.codeparameters = ast.CodeParameters(selfparam, params, cparam.paramnames, cparam.defaults, vparam, kparam, cparam.returnparams)

		self.currentFrame = frame
		self.frames[node] = frame

	@dispatch(cfg.Exit)
	def visitCFGLeaf(self, node):
		pass

	@dispatch(cfg.Suite)
	def visitCFGSuite(self, node):
		self.currentFrame = dict(self.frames[node.prev])

		ops = []
		for op in node.ops:
			result = self(op)
			if result is not None:
				ops.append(result)
		node.ops = ops

		self.frames[node] = self.currentFrame

	@dispatch(cfg.Switch)
	def visitCFGSwitch(self, node):
		self.currentFrame = dict(self.frames[node.prev])

		node.condition = self(node.condition)

		self.frames[node] = self.currentFrame

	@dispatch(cfg.TypeSwitch)
	def visitTypeSwitch(self, node):
		self.currentFrame = dict(self.frames[node.prev])

		conditional = self(node.original.conditional)


		cases = []
		for i, case in enumerate(node.original.cases):
			if case.expr:
				# TODO slightly unsound, modifies the expressions in the wrong frame.
				expr = self.clone(case.expr, self.currentFrame)

				cases.append(ast.TypeSwitchCase(case.types, expr, case.body))
			else:
				cases.append(case)


		node.original = ast.TypeSwitch(conditional, cases)

		self.frames[node] = self.currentFrame



	@dispatch(cfg.Yield)
	def visitCFGYield(self, node):
		self.currentFrame = dict(self.frames[node.prev])
		self.frames[node] = self.currentFrame

	@dispatch(cfg.Merge)
	def visitCFGMerge(self, node):
		# Copy a previous frame, any previous frame.
		frame = None
		complete = True
		for prev in node.reverse():
			if prev in self.frames:
				if frame is None:
					frame = dict(self.frames[prev])
			else:
				complete = False

		# Mask variables that need to be merged.
		if node in self.merge:
			for name in self.merge[node]:
				frame[name] = name.clone()

			self.fixup.append(node)

		self.frames[node] = frame

	@dispatch(ast.Local)
	def visitLocal(self, node):
		result = self.currentFrame[node]
		self.read.add(result)
		return result

	@dispatch(ast.InputBlock)
	def visitInputBlock(self, node):
		return ast.InputBlock([ast.Input(input.src, self.clone(input.lcl, self.currentFrame)) for input in node.inputs])

	@dispatch(ast.OutputBlock)
	def visitOutputBlock(self, node):
		return ast.OutputBlock([ast.Output(self(output.expr), output.dst) for output in node.outputs])


	@dispatch(ast.BinaryOp, ast.Call, ast.ConvertToBool, ast.UnaryPrefixOp, ast.BuildTuple, ast.Return, ast.DirectCall,
			ast.Is,
			ast.GetGlobal, ast.SetGlobal, ast.DeleteGlobal,
			ast.GetAttr, ast.SetAttr, ast.DeleteAttr,
			ast.GetSubscript, ast.SetSubscript, ast.DeleteSubscript,
			ast.Allocate, ast.Load, ast.Store, ast.Check)
	def visitOK(self, node):
		return node.rewriteChildren(self)

	@dispatch(ast.Discard)
	def visitDiscard(self, node):
		result = node.rewriteChildren(self)
		if isinstance(node, ast.Existing):
			return None
		return result

	@dispatch(ast.leafTypes, ast.Existing, ast.GetCellDeref, ast.Code, ast.DoNotCare)
	def visitASTLeaf(self, node):
		return node

	@dispatch(ast.Assign)
	def visitAssign(self, node):
		expr = self(node.expr)
		if isinstance(expr, (ast.Local, ast.Existing)):
			if len(node.lcls) == 1:
				# Reach
				self.currentFrame[node.lcls[0]] = expr
				return None

		lcls = [self.clone(lcl, self.currentFrame) for lcl in node.lcls]
		return ast.Assign(expr, lcls)

	@dispatch(ast.UnpackSequence)
	def visitUnpackSequence(self, node):
		expr = self(node.expr)

		lcls = [self.clone(lcl, self.currentFrame) for lcl in node.targets]
		return ast.UnpackSequence(expr, lcls)


	# Insert the merges, now that we know all the sources
	def doFixup(self):
		merges = []

		changed = True

		for merge in self.fixup:
			for name in self.merge[merge]:
				merges.append((merge, name))

		while merges and changed:
			changed = False
			defer = []

			for merge, name in merges:
				target = self.frames[merge][name]

				if target in self.read:

					arguments = []
					for prev in merge.reverse():
						arguments.append(self.frames[prev].get(name))

					self.read.update(arguments)

					phi = ast.Phi(arguments, target)
					merge.phi.append(phi)

					changed = True
				else:
					defer.append((merge, name))

			merges = defer


def evaluate(compiler, g):
	# Analysis

	def forward(node):
		return node.forward()

	def bind(node, djnode):
		node.data = djnode

	dom.evaluate([g.entryTerminal], forward, bind)

	# Transform

	cm = CollectModifies()
	dfs = CFGDFS(post=cm)
	dfs.process(g.entryTerminal)

	# Find the what variables we be renamed at what merge points
	renames = set()
	merges = {}

	# TODO linear verions of idf?
	for k, v in cm.mod.iteritems():
		idf = set()
		pending = set()
		pending.update(v)

		while pending:
			djnode = pending.pop()
			for child in djnode.idf:
				if child not in idf:
					idf.add(child)
					pending.add(child)

		for djnode in idf:
			if not djnode.node in merges:
				merges[djnode.node] = set()
			merges[djnode.node].add(k)

		if idf:
			renames.add(k)


	order = cm.order
	order.reverse()

	ssar = SSARename(g, renames, merges)
	for node in order:
		ssar(node)
	ssar.doFixup()
