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

from language.python.program import Object
from analysis import programculler


# Eliminates all unreferenced code from a given program
class CodeContextCuller(TypeDispatcher):
	# Critical: code references in direct calls must NOT have their annotations rewritten.
	@dispatch(ast.leafTypes, ast.Code)
	def visitLeaf(self, node):
		pass

	@dispatch(ast.Local)
	def visitLocal(self, node):
		if node not in self.locals:
			self.locals.add(node)
			node.annotation = node.annotation.contextSubset(self.remap)

	@defaultdispatch
	def default(self, node):
		assert not node.__shared__, type(node)
		node.visitChildren(self)
		if node.annotation is not None:
			node.annotation = node.annotation.contextSubset(self.remap)

	def process(self, code, contexts):
		self.locals = set()
		self.remap  = []

		for cindex, context in enumerate(code.annotation.contexts):
			if context in contexts:
				self.remap.append(cindex)

		code.annotation = code.annotation.contextSubset(self.remap)

		code.visitChildrenForced(self)


def evaluateCode(code, contexts, ccc):
	# Check invariant
	for context in contexts:
		assert context in code.annotation.contexts, (code, id(context))

	if len(code.annotation.contexts) != len(contexts):
		ccc.process(code, contexts)

	# Check invariant
	for context in contexts:
		assert context in code.annotation.contexts, (code, id(context))

def evaluate(compiler, prgm):
	with compiler.console.scope('cull'):
		liveContexts = programculler.findLiveContexts(prgm)

		ccc = CodeContextCuller()
		for code, contexts in liveContexts.iteritems():
			evaluateCode(code, contexts, ccc)

		prgm.liveCode = set(liveContexts.iterkeys())
