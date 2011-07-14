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
from language.python.shaderprogram import VSContext, FSContext
from optimization import rewrite
from optimization import loadelimination, storeelimination, simplify

from . import common

from .. import intrinsics


from . shaderdescription import *

class FindReturns(TypeDispatcher):

	@dispatch(ast.leafTypes, ast.CodeParameters, ast.Local, ast.Existing, ast.Assign, ast.Discard, ast.Store)
	def visitLeaf(self, node):
		pass

	@dispatch(ast.Suite, ast.Switch, ast.Condition, ast.TypeSwitch, ast.TypeSwitchCase, ast.While)
	def visitOK(self, node):
		node.visitChildren(self)

	@dispatch(ast.Return)
	def visitReturn(self, node):
		self.returns.append(node)

	def process(self, code):
		self.returns = []
		code.visitChildrenForced(self)
		return self.returns

class OutputFlattener(object):
	def __init__(self, compiler, prgm, code, fs):
		self.compiler = compiler
		self.prgm = prgm
		self.code = code
		self.fs   = fs

	def generateExisting(self, object):
		ex = ast.Existing(object)

		region = self.prgm.storeGraph.regionHint
		xtype = self.prgm.storeGraph.canonical.existingType(object)
		obj = region.object(xtype)

		refs = common.annotationFromValues(self.code, (obj,))
		ex.rewriteAnnotation(references=refs)

		return ex


	def generateTypeLoad(self, expr, fieldName, refs):
		pt = refs[0].xtype.obj.pythonType()

		for ref in refs[1:]:
			assert ref.xtype.obj.pythonType is pt, "Temporary Limitation"

		ex = self.generateExisting(self.compiler.extractor.getObject(pt))

		name = common.nameForField(self.compiler, fieldName)

		lcl = ast.Local(name)
		lcl.annotation = ex.annotation

		self.statements.append(ast.Assign(ex, [lcl]))

		return lcl

	def generateLoad(self, expr, fieldName, refs):
		if fieldName.type == 'LowLevel' and fieldName.name.pyobj == 'type':
			# This a kludge until IPA works.
			return self.generateTypeLoad(expr, fieldName, refs)

		fields = []
		for ref in refs:
			fields.append(ref.knownField(fieldName))

		lcl = common.localForFieldSlot(self.compiler, self.code, fields[0], fields)

		exname = self.generateExisting(fieldName.name)
		load = ast.Load(expr, fieldName.type, exname)

		empty = common.emptyAnnotation(self.code)

		load.rewriteAnnotation(allocates=empty, modifies=empty, reads=common.annotationFromValues(self.code, fields))

		self.statements.append(ast.Assign(load, [lcl]))

		return lcl

	def handleTree(self, root, slot):
		refs = slot.annotation.references.merged

		assert refs

		if len(refs) > 1:
			fields = frozenset(refs[0].slots.iterkeys())
			for ref in refs[1:]:
				assert fields == frozenset(ref.slots.iterkeys()), "Output tree is not certain"

		for fieldName in refs[0].slots.iterkeys():
			if not intrinsics.isIntrinsicField(fieldName):
				fieldslot = self.generateLoad(slot, fieldName, refs)
				fieldroot = root.field(fieldName, fieldslot)
				self.handleTree(fieldroot, fieldslot)



	def returnNone(self):
		self.statements.append(ast.Return([self.generateExisting(self.compiler.extractor.getObject(None))]))

	def loadFromContext(self, contextType, name):
			slotName = self.compiler.slots.uniqueSlotName(getattr(contextType, name))
			slotName = self.compiler.extractor.getObject(slotName)

			canonical = self.prgm.storeGraph.canonical
			fieldName = canonical.fieldName('Attribute', slotName)

			expr = self.code.codeparameters.params[1]
			refs = expr.annotation.references.merged

			outputslot = self.generateLoad(expr, fieldName, refs)

			return outputslot

	def makeTree(self, slot):
		root = TreeNode(slot)
		self.handleTree(root, slot)
		return root

	def processReturn(self, ret):
		self.statements = []

		if self.fs:
			outputslot = self.loadFromContext(FSContext, 'colors')
		else:
			assert len(ret.exprs) == 1
			outputslot = ret.exprs[0]

		root = self.makeTree(outputslot)
		outtuple = root.extractTuple()

		if self.fs:
			outdesc = FSOutputDescription()
			outdesc.colors = outtuple

			try:
				depthslot = self.loadFromContext(FSContext, 'depth')
				outdesc.depth = self.makeTree(depthslot)
			except:
				outdesc.depth = None

		else:
			outdesc = VSOutputDescription()
			outdesc.varying = outtuple
			posslot = self.loadFromContext(VSContext, 'position')

			outdesc.position = self.makeTree(posslot)

		block = outdesc.generateOutputStatements()
		self.statements.append(block)

		self.returnNone()

		#print
		#for stmt in self.statements:
		#	print stmt
		#print


		desc = ShaderDescription()
		desc.outputs = outdesc
		return desc, self.statements

	def process(self):
		returns = FindReturns().process(self.code)

		assert len(returns) == 1, "Temporary Limitation: only one return per shader"

		rewrites = {}

		for ret in returns:
			desc, rewrites[ret] = self.processReturn(ret)

		rewrite.rewrite(self.compiler, self.code, rewrites)

		# HACK
		while loadelimination.evaluateCode(self.compiler, self.prgm, self.code, simplify=False):
			pass

		#simplify.evaluateCode(self.compiler, self.prgm, self.code)
		#storeelimination.evaluate(self.compiler, self.prgm, simplify=False)

		simplify.evaluateCode(self.compiler, self.prgm, self.code)

		return desc

def process(compiler, prgm, code, fs):
	of = OutputFlattener(compiler, prgm, code, fs)
	return of.process()
