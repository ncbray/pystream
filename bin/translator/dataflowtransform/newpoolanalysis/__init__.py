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

from ... import intrinsics

import collections
from PADS.UnionFind import UnionFind

from analysis.storegraph import storegraph

from . import prepass, shaderanalysis


from . model import *

from .. import bind


class FieldGroup(object):
	def __init__(self, name, fields, poolInfo):
		self.name     = name
		self.fields   = fields
		self.poolInfo = poolInfo

		poolInfo.fieldGroupsRefer.append(self)

	def __repr__(self):
		return "FieldGroup(%r)" % (self.name,)

class PoolGraphBuilder(TypeDispatcher):
	def __init__(self, exgraph, ioinfo):
		self.exgraph = exgraph
		self.ioinfo  = ioinfo
		self.poolInfos  = {}
		self.fieldInfos = {}
		self.typeIDs    = {}
		self.uid = 0

		self.dirty = set()

		self.lut = SubpoolLUT()

		self.compatable = UnionFind()

		self.active = True

	def reads(self, args):
		self.compatable.union(*args)

	def modifies(self, args):
		self.compatable.union(*args)


	def ambiguousTypes(self, types):
		for t in types:
			if not t in self.typeIDs:
				self.typeIDs[t] = self.uid
				self.uid += 1

	def linkContainedFieldGroups(self, fgs):
		lut = collections.defaultdict(list)

		for fg in fgs:
			objs = set([field.object for field in fg.fields])
			for obj in objs:
				lut[obj].append(fg)

		for info in self.getUniquePools():
			infoFGs = set()
			for ref in info.refs:
				infoFGs.update(lut[ref])
			info.containedFieldGroups = tuple(infoFGs)

	def fieldGroups(self):
		groups = {}
		for obj, group in self.compatable.parents.iteritems():
			if group not in groups:
				groups[group] = [obj]
			else:
				groups[group].append(obj)

		fgs = []
		for name, group in groups.iteritems():
			fg = FieldGroup(name, group, self.fieldInfo(name))
			fgs.append(fg)

		# TODO compress mutually exclusive field groups?
		self.linkContainedFieldGroups(fgs)

		# Create an index
		for fg in fgs:
			for field in fg.fields:
				self.fieldInfos[field] = fg

		return fgs

	def markDirty(self, info):
		assert not info.dirty
		info.dirty = True
		self.dirty.add(info)

	def isAnchor(self, slot):
		return slot in self.ioinfo.outputs or slot in self.ioinfo.uniforms or slot in self.ioinfo.inputs

	def localInfo(self, slot):
		info = self.poolInfo(slot, slot.annotation.references.merged)
		info.anchor = self.isAnchor(slot)
		return info

	def fieldInfo(self, slot):
		return self.poolInfo(slot, slot)

	def poolInfoIfExists(self, slot):
		return self.poolInfos.get(slot)

	def poolInfo(self, slot, refs, output=False):
		if slot not in self.poolInfos:
			assert self.active, slot

			info = ReferenceInfo(output)
			info.addSlot(slot)
			for ref in refs:
				info.addRef(ref)

			self.poolInfos[slot] = info
			self.markDirty(info)
		else:
			info = self.poolInfos[slot]
			forward = info.forward()
			if info is not forward:
				self.poolInfos[slot] = forward
				info = forward
		return info

	@dispatch(ast.leafTypes, ast.Code, ast.CodeParameters, ast.Return, ast.Existing, ast.DoNotCare)
	def visitLeafs(self, node):
		pass

	@dispatch(ast.Local)
	def visitLocal(self, node):
		return self.localInfo(node)

	@dispatch(ast.DirectCall, ast.Call, ast.Allocate, ast.Load, ast.Discard)
	def visitOp(self, node):
		node.visitChildren(self)

	@dispatch(ast.Assign)
	def visitAssign(self, node):
		self(node.expr)

		if isinstance(node.expr, ast.Local):
			expr = self.localInfo(node.expr)
			target = self.localInfo(node.lcls[0])

			expr.transfer(self, target)

		elif isinstance(node.expr, ast.Load):
			load = node.expr
			expr = self.localInfo(load.expr)
			target = self.localInfo(node.lcls[0])

			self.reads(load.annotation.reads.merged)

			src = None
			for field in load.annotation.reads.merged:
				fieldInfo = self.fieldInfo(field)
				if src is None:
					src = fieldInfo
				else:
					src = src.merge(self, fieldInfo)

			src.transfer(self, target)

	@dispatch(ast.InputBlock)
	def visitInputBlock(self, node):
		for input in node.inputs:
			# HACK ionames are not annotated?
			src = self.poolInfo(input.src, input.lcl.annotation.references.merged)
			src.anchor = True

			lcl = self.localInfo(input.lcl)

			src.transfer(self, lcl)

	@dispatch(ast.OutputBlock)
	def visitOutputBlock(self, node):
		for output in node.outputs:
			expr = self.localInfo(output.expr)
			dst = self.poolInfo(output.dst, output.expr.annotation.references.merged, output=True)
			dst.anchor = True

			# TODO no merge?
			expr.transfer(self, dst)

	@dispatch(ast.Store)
	def visitStore(self, node):
		self.modifies(node.annotation.modifies.merged)

		node.visitAllChildren(self)

		if isinstance(node.value, ast.Local):

			value = self.localInfo(node.value)

			expr  = self.localInfo(node.expr)


			target = None
			for field in node.annotation.modifies.merged:
				fieldInfo = self.fieldInfo(field)
				if target is None:
					target = fieldInfo
				else:
					target = target.merge(self, fieldInfo)

			value.transfer(self, target)

	@dispatch(ast.TypeSwitch)
	def visitTypeSwitch(self, node):
		cond = self.localInfo(node.conditional)
		for case in node.cases:
			expr = self.localInfo(case.expr)
			cond = cond.transfer(self, expr)
			self(case.body)

	@dispatch(ast.Suite, ast.Switch, ast.Condition, ast.While)
	def visitOK(self, node):
		node.visitChildren(self)


	def analyzeCode(self, code):
		code.visitChildrenForced(self)

	def process(self):
		while self.dirty:
			info = self.dirty.pop()
			info.dirty = False
			info.contract(self)

		for info in self.getUniquePools():
			info.postProcess(self.exgraph)

			if len(info.types) > 1:
				self.ambiguousTypes(info.types)


		for sub in self.getUniqueSubpools():
			sub.postProcess(self.exgraph)

		self.fieldGroups()

	def getUniquePools(self):
		unique = set()

		for info in self.poolInfos.itervalues():
			unique.add(info.forward())

		return unique

	def getUniqueSubpools(self):
		unique = set()
		for info in self.poolInfos.itervalues():
			for subpool in info.lut.subpools.itervalues():
				unique.add(subpool.forward())
		return unique

	def dump(self):
		for info in self.getUniqueSubpools():
			print "SLOTS"
			for slot in info.slots:
				print '\t', slot
			print "REFS"
			for ref in info.refs:
				print '\t', ref, ref.annotation.final
			print "VOLATILE", info.volatile
			print "UNIQUE  ", info.unique
			print "U/I/A   ", info.uniform, info.input, info.allocated
			print
		return

		for info in self.getUniquePools():
			print "SLOTS"
			for slot in info.slots:
				print '\t', slot
			print "TYPES"
			for t in info.types:
				print '\t', t
			print "REFS"
			for ref in info.refs:
				print '\t', ref, ref.annotation.final
			print "GROUPS REFER"
			for fg in info.fieldGroupsRefer:
				print '\t', fg
			print "GROUPS CONTAINED"
			for fg in info.containedFieldGroups:
				print '\t', fg

			print "FINAL ", info.final
			print "UNIQUE", info.unique

			for name, sub in info.lut.subpools.iteritems():
				print '\t', name, sub.volatile
				print '\t', sub.refs
			print
		print

def process(compiler, prgm, shaderprgm, exgraph, ioinfo, *contexts):
	prepassInfo = prepass.process(compiler, prgm, exgraph, ioinfo, contexts)

	for context in contexts:
		shaderanalysis.process(compiler, prgm, exgraph, ioinfo, prepassInfo, context, shaderprgm)

	bind.generateBindingClass(compiler, prgm, shaderprgm, prepassInfo)

	return

	pgb = PoolGraphBuilder(exgraph, ioinfo)

	for context in contexts:
		code = context.code
		#print code
		pgb.analyzeCode(code)

	pgb.process()

	pgb.active = False

	pgb.dump()

	return pgb
