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

from . import model

class PoolAnalysis(TypeDispatcher):
	def __init__(self, exgraph, ioinfo, prepassInfo):
		self.exgraph = exgraph
		self.ioinfo = ioinfo
		self.prepassInfo = prepassInfo

		self.refInfos = {}

		self.objInfos = {}

		self.liveReads = set()
		self.liveModifies = set()

		self.dirty = set()

		self.renamer = model.Renamer()

	def reads(self, fields):
		self.liveReads.update(fields)

	def modifies(self, fields):
		self.liveModifies.update(fields)

	def objInfo(self, obj):
		if obj not in self.objInfos:
			objInfo = model.ObjectInfo(obj)
			self.objInfos[obj] = objInfo
		else:
			objInfo = self.objInfos[obj]
		return objInfo

	def registerRef(self, obj, subinfo):
		objInfo = self.objInfo(obj)
		objInfo.subrefs.add(subinfo)

	def initRef(self, slot, refs):
		if slot not in self.refInfos:
			info = model.ReferenceInfo()
			info.addSlot(slot)
			for ref in refs:
				subinfo = info.addRef(ref)
				if subinfo:
					self.registerRef(ref, subinfo)

			self.refInfos[slot] = info

	def refInfo(self, slot):
		info = self.refInfos[slot]
		forward = info.forward()
		if info is not forward:
			self.refInfos[slot] = forward
			info = forward
		return info

	@dispatch(ast.leafTypes, ast.Code, ast.CodeParameters, ast.Return, ast.Existing, ast.DoNotCare, ast.IOName)
	def visitLeafs(self, node):
		pass

	@dispatch(ast.Local)
	def visitLocal(self, node):
		return self.initRef(node, node.annotation.references.merged)

	@dispatch(ast.Load)
	def visitLoad(self, node):
		self.reads(node.annotation.reads.merged)
		node.visitChildren(self)

	@dispatch(ast.Store)
	def visitStore(self, node):
		self.modifies(node.annotation.modifies.merged)
		node.visitChildren(self)


	@dispatch(ast.Suite, ast.Switch, ast.Condition, ast.While, ast.TypeSwitch, ast.TypeSwitchCase,
			ast.InputBlock, ast.Input, ast.OutputBlock, ast.Output,
			ast.DirectCall, ast.Call, ast.Allocate, ast.Discard, ast.Assign)
	def visitOK(self, node):
		node.visitChildren(self)

	def markInitialVolatile(self):
		for obj, info in self.objInfos.iteritems():
			if obj in self.prepassInfo.volatileIntrinsics:
				info.markVolatile(self)

	def resolveVolatile(self):
		self.markInitialVolatile()

		#print
		#print "resolving"

		while self.dirty:
			current = self.dirty.pop()
			#print current.name
			current.resolve(self)
			#print

	def resolveNames(self):
		for slot, refInfo in self.refInfos.iteritems():
			name = slot.name
			if name is None:
				name = 'bogus'
			name = 'lcl_'+name

			for ref in slot.annotation.references.merged:
				refInfo.addRef(ref)

			refInfo.postProcess()
			refInfo.setName(name, self.renamer)

#		print "shader names"
#		for group, refInfo in self.refInfos.iteritems():
#			print refInfo.name, refInfo.mode
#			for sub in refInfo.subpools():
#				print '\t', sub.name
#		print

	def processCode(self, code):
		code.visitChildrenForced(self)

		self.resolveVolatile()
		self.resolveNames()


from .. import glsltranslatortwo

def process(compiler, prgm, exgraph, ioinfo, prepassInfo, context, shaderprgm):
	pa = PoolAnalysis(exgraph, ioinfo, prepassInfo)
	pa.processCode(context.code)

	glsltranslatortwo.processCode(compiler, prgm, exgraph, ioinfo, prepassInfo, pa, context, shaderprgm)
