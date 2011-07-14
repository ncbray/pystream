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

from util.graphalgorithim.merge import serializeMerges

class Expander(TypeDispatcher):
	@defaultdispatch
	def default(self, node):
		pass

	def createTemp(self, node):
		return node.clone()

	@dispatch(cfg.Merge)
	def visitMerge(self, node):
		if node.phi:
			for i, (prev, prevName) in enumerate(node.iterprev()):
				transfer = [(phi.arguments[i], phi.target) for phi in node.phi if phi.arguments[i] is not None]
				if not transfer:
					continue

				# HACK can't handle pushing assignments up into exceptions?
				assert prevName in ('normal', 'true', 'false', 'entry'), prevName

				transfer, temps = serializeMerges(transfer, self.createTemp)

				stmts = [ast.Assign(src, [dst]) for src, dst in transfer]

				suite = cfg.Suite(prev.region)
				suite.ops = stmts

				prev.insertAtExit(prevName, suite, 'normal')

			node.phi = []

def evaluate(compiler, g):
	ex = Expander()
	CFGDFS(post=ex).process(g.entryTerminal)
