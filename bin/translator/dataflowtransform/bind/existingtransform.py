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


class ExistingTransform(TypeDispatcher):
	__slots__ = 'compiler'

	def __init__(self, compiler):
		self.compiler = compiler

	def getPath(self, parts):
		result = ast.GetGlobal(ast.Existing(self.compiler.extractor.getObject(parts.pop(0))))

		for part in parts:
			result = ast.GetAttr(result, ast.Existing(self.compiler.extractor.getObject(part)))

		return result

	@dispatch(str, type(None), ast.Local, ast.Code)
	def visitLeaf(self, node):
		return node

	@dispatch(ast.Existing)
	def visitExisting(self, node):
		if node.object.isLexicalConstant():
			# This can be embedded in the code
			return node
		else:
			t = node.object.pythonType()
			if t is type:
				obj = node.object.pyobj
				# HACK convert a type reference into a dotted path
				module = obj.__module__
				name   = obj.__name__

				parts = module.split(".")
				parts.append(name)

				return self.getPath(parts)
			else:
				assert False, node

	@dispatch(ast.FunctionDef)
	def visitFunctionDef(self, node):
		# Transform code contained by function defs
		code = node.code.replaceChildren(self)
		decorators = [decorator.rewriteChildren(self) for decorator in node.decorators]
		return ast.FunctionDef(node.name, code, decorators)

	@dispatch(ast.ClassDef, ast.GetGlobal, ast.CodeParameters, ast.Suite,
			ast.Switch, ast.Condition, ast.Assert,
			ast.Assign, ast.Discard,
			ast.Call, ast.GetAttr)
	def visitOK(self, node):
		return node.rewriteChildren(self)

# Make existing references realizable in standard Python code
def evaluateAST(compiler, node):
	return ExistingTransform(compiler)(node)
