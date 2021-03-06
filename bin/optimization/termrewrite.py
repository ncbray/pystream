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

from language.python import ast
from language.python import program
from language.python import annotations

def isZero(arg):
	return isinstance(arg, ast.Existing) and arg.object.isConstant() and arg.object.pyobj == 0

def isOne(arg):
	return isinstance(arg, ast.Existing) and arg.object.isConstant() and arg.object.pyobj == 1

def isNegativeOne(arg):
	return isinstance(arg, ast.Existing) and arg.object.isConstant() and arg.object.pyobj == -1

def hasNumArgs(node, count):
	return len(node.args) == count and isSimpleCall(node)

def isSimpleCall(node):
	return not node.kwds and not node.vargs and not node.kargs


def isAnalysisInstance(node, type):
	if isinstance(node, ast.Existing) and node.object.isConstant():
		return isinstance(node.object.pyobj, type)
	elif isinstance(node, ast.Local):
		if not node.annotation.references[0]:
			return False

		for ref in node.annotation.references[0]:
			obj = ref.xtype.obj
			if not issubclass(obj.pythonType(), type):
				return False
		return True

	return False

def isAnalysis(arg, tests):
	return isinstance(arg, ast.Existing) and isinstance(arg.object, program.Object) and arg.object.pyobj in tests

class DirectCallRewriter(object):
	def __init__(self, extractor):
		self.extractor = extractor
		self.exports = extractor.stubs.exports if hasattr(extractor, 'stubs') else {}
		self.rewrites = {}

	def _getOrigin(self, func):
		if func in self.extractor:
			obj = self.extractor.getObject(func)
			return self.extractor.desc.origin.get(obj)

	def addRewrite(self, name, func):
		code = self.exports.get(name)
		self._bindCode(code, func)

	def attribute(self, type, name, func):
		attr = type.__dict__[name]
		origin = self._getOrigin(attr)
		self._bindOrigin(origin, func)

	def function(self, obj, func):
		origin = self._getOrigin(obj)
		self._bindOrigin(origin, func)

	def _bindCode(self, code, func):
		if code:
			origin = code.annotation.origin
			self._bindOrigin(origin, func)

	def _bindOrigin(self, origin, func):
		if origin not in self.rewrites:
			self.rewrites[origin] = [func]
		else:
			self.rewrites[origin].append(func)

	def __call__(self, strategy, node):
		origin = node.code.annotation.origin
		if origin in self.rewrites:
			for rewrite in self.rewrites[origin]:
				result = rewrite(strategy, node)
				if result is not None:
					return result
		return None
