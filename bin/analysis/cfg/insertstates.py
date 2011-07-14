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
from language.chameleon import ast, cfg
from . dfs import CFGDFS

class StateInserter(TypeDispatcher):
	def __init__(self):
		self.states = []

	@dispatch(cfg.Entry, cfg.Merge)
	def visitIgnore(self, node):
		pass

	@dispatch(cfg.Switch, cfg.Yield, cfg.Suite)
	def visitOK(self, node):
		if isinstance(node.prev, (cfg.Entry, cfg.Yield, cfg.Merge)):
			state = cfg.State(len(self.states))
			self.states.append(state)
			node.redirectEntries(state)
			state.setExit('normal', node)

	@dispatch(cfg.Exit)
	def visitExit(self, node):
		pass

def evaluate(compiler, g):
	inserter = StateInserter()
	dfs = CFGDFS(pre=inserter)
	dfs.process(g.entryTerminal)
	return inserter.states
