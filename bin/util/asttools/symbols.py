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

class SymbolBase(object):
	__slots__ = ()

class Symbol(SymbolBase):
	__slots__ = ('name',)
	def __init__(self, name):
		self.name = name

	def __repr__(self):
		return '{%s}' % self.name

class Extract(SymbolBase):
	__slots__ = ('child',)
	def __init__(self, child):
		self.child = child

class SymbolRewriter(TypeDispatcher):
	def __init__(self, extractor, template):
		self.extractor = extractor
		self.template = template
		self.lut = None

	def sharedTemplate(self):
		return not isinstance(self.template, list) and self.template.__shared__

	@dispatch(Symbol)
	def visitSymbol(self, node):
		return self.lut.get(node.name, node)

	@dispatch(Extract)
	def visitExtract(self, node):
		return self.extractor.getObject(self(node.child))

	@dispatch(str, int, float, type(None))
	def visitLeaf(self, node):
		return node

	@defaultdispatch
	def default(self, node):
		return node.rewriteChildren(self)

	# Will not be invoked by traversal functions,
	# included so groups of nodes can be rewritten
	@dispatch(list)
	def visitList(self, node):
		return [self(child) for child in node]

	# the self parameter is intentionally mangled to avoid messing with the kargs
	def rewrite(__self__, **lut):
		__self__.lut = lut
		if __self__.sharedTemplate():
			result = __self__.template.rewriteChildrenForced(__self__)
		else:
			result = __self__(__self__.template)
		__self__.lut = None
		return result

def rewrite(extractor, template, **kargs):
	# TODO check that all arguments are used
	return SymbolRewriter(extractor, template).rewrite(**kargs)
