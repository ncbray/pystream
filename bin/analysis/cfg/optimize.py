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
from . dfs import CFGDFS
from language.python import ast
from . import graph as cfg

class CFGOptPost(TypeDispatcher):
	def __init__(self, compiler):
		self.compiler = compiler

	def isConst(self, node):
		# HACK unsound
		return isinstance(node, ast.Existing)

	def constToBool(self, node):
		return bool(node.object.pyobj)

	@dispatch(cfg.Switch)
	def visitSwitch(self, node):
		if self.isConst(node.condition):
			result = self.constToBool(node.condition)

			normal = (node.getExit('true'), 'true')
			culled = (node.getExit('false'), 'false')

			if not result:
				normal, culled = f, t

			suite = cfg.Suite(node.region)
			suite.setExit('fail', node.getExit('fail'))
			suite.setExit('error', node.getExit('error'))

			if not isinstance(node.condition, ast.Existing):
				suite.ops.append(ast.Discard(node.condition))

			node.redirectEntries(suite)

			# TODO don't remove prev, redirect?
			normal[0].removePrev(node, normal[1])
			culled[0].removePrev(node, culled[1])
			suite.setExit('normal', normal[0])

			# Process the suite
			self(suite)

	@defaultdispatch
	def default(self, node):
		pass

	def exitMatchesOrNone(self, a, b, name):
		ae = a.getExit(name)
		be = b.getExit(name)
		return ae is None or be is None or ae is be

	def nonlocalFlowMatches(self, a, b):
		return self.exitMatchesOrNone(a, b, 'fail') and self.exitMatchesOrNone(a, b, 'error')

	@dispatch(cfg.Merge)
	def visitMerge(self, node):
		node.simplify()

	@dispatch(cfg.Suite)
	def visitSuite(self, node):
		if len(node.ops) == 0:
			# This is importaint, as it prevents extranious fail/error
			# flow from attaching itself to another block
			node.simplify()
			return

		normal = node.getExit('normal')
		if normal is not None and isinstance(normal, cfg.Suite):
			if self.nonlocalFlowMatches(node, normal):
				# Contact the next suite into this one
				node.ops.extend(normal.ops)

				node.forwardExit(normal, 'normal')

				if node.getExit('fail') is None:
					node.stealExit(normal, 'fail')

				if node.getExit('error') is None:
					node.stealExit(normal, 'error')

def evaluate(compiler, g):
	post = CFGOptPost(compiler)
	dfs  = CFGDFS(post=post)
	dfs.process(g.entryTerminal)
