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
from . import graph as cfg
from . dfs import CFGDFS

# Kills unreachable CFG nodes

class Logger(TypeDispatcher):
	def __init__(self):
		self.merges = []

	@defaultdispatch
	def default(self, node):
		pass

	@dispatch(cfg.MultiEntryBlock)
	def visitMerge(self, node):
		self.merges.append(node)

def evaluate(compiler, g):
	logger = Logger()
	dfs = CFGDFS(post=logger)
	dfs.process(g.entryTerminal)

	def live(node):
		return node in dfs.processed

	for merge in logger.merges:
		for prev in merge._prev:
			assert isinstance(prev, tuple), merge._prev

		# HACK exposes the internals of merge
		filtered = [prev for prev in merge._prev if live(prev[0])]
		merge._prev = filtered
