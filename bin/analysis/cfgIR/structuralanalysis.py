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
from . import cfg

from PADS.DFS import postorder

class BlockWrapper(object):
	def __getitem__(self, key):
		return key.iternext()

def cfgPostorder(root):
	return list(postorder(BlockWrapper(), root))


class CFGEdge(object):
	def __init__(self, src, dst):
		self.src = src
		self.dst = dst

class StructuralAnalyzer(TypeDispatcher):
	@defaultdispatch
	def visitDefault(self, node):
		return node

	@dispatch(cfg.CFGBranch)
	def visitBranch(self, node):
		if node.op.isTypeSwitch():
			entry = node.prev

			switch = node

			cases = []
			exitCases  = []

			oldmerge = None
			for next in node.iternext():
				# TODO make sure it's SESE?
				assert next.numOut() <= 1

				cases.append(next)

				# The next.next block must either be a merge or None.
				if next.numOut() == 1:
					assert isinstance(next.next, cfg.CFGMerge), next.next
					if oldmerge is None:
						oldmerge = next.next
					else:
						# Must merge to the same merge node.
						assert oldmerge is next.next

					exitCases.append(next)

			# Redirect the merges
			newmerge = self.seperateMerge(oldmerge, exitCases)

			switchCFG = cfg.CFGTypeSwitch(switch, cases, newmerge)

			if oldmerge:
				switchCFG.addNext(oldmerge)
				oldmerge.optimize()

			node = switchCFG
		else:
			pass

		return node


	def seperateMerge(self, oldmerge, cases):
		newmerge = cfg.CFGMerge()
		for case in cases:
			case.replaceNext(oldmerge, newmerge)
		return newmerge

	def insertHead(self, node, next):
		if not next.isSuite():
			next = cfg.CFGSuite(next)
		next.insertHead(node)
		return next

	def contract(self, node):
		if node.isLinear():
			next = node.next
			"CONTRACT?", node, next
			if next is not None and next.isLinear():
				return self.insertHead(node, next)
		return node

	def process(self, root):
		post = cfgPostorder(root)

		for node in post:
			result = self(node)
			result = self.contract(result)

		# This should be the head.
		return result

def processCFG(compiler, cfgHead):
	sa = StructuralAnalyzer()
	return sa.process(cfgHead)
