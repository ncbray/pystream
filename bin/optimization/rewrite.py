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

import optimization.simplify
from util.typedispatch import *

# HACK necessary to get leaf types.  Sadly, it makes this optimization less than generic
from language.python import ast

class Rewriter(TypeDispatcher):
	def __init__(self, replacements):
		TypeDispatcher.__init__(self)
		self.replacements = replacements
		self.replaced = set()

	@dispatch(ast.leafTypes)
	def visitLeaf(self, node):
		if node in self.replaced:
			return node

		if node in self.replacements:
			oldnode = node
			self.replaced.add(oldnode)
			node = self(self.replacements[node])
			self.replaced.remove(oldnode)

		return node

	@dispatch(list, tuple)
	def visitContainer(self, node):
		# AST nodes may sometimes be replaced with containers,
		# so unlike most transformations, this will get called.
		return [self(child) for child in node]

	@defaultdispatch
	def visitNode(self, node):
		# Prevent stupid recursion, where the replacement
		# contains the original.
		if node in self.replaced:
			return node

		if node in self.replacements:
			oldnode = node
			self.replaced.add(oldnode)
			node = self(self.replacements[node])
			self.replaced.remove(oldnode)
		else:
			node = node.rewriteChildren(self)

		return node

	def processCode(self, code):
		code.replaceChildren(self)
		return code

def rewriteTerm(term, replace):
	if replace:
		term = Rewriter(replace)(term)
	return term

def rewrite(compiler, code, replace):
	if replace:
		Rewriter(replace).processCode(code)
	return code

def rewriteAndSimplify(compiler, prgm, code, replace):
	if replace:
		Rewriter(replace).processCode(code)
		optimization.simplify.evaluateCode(compiler, prgm, code)
	return code
