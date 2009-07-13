from asttools.transform import *
from language.python import ast

import collections

from analysis import programculler
from PADS.StrongConnectivity import StronglyConnectedComponents

def isSCC(g):
	for k, v in g.iteritems():
		if v:
			return True
	return False


def findRecursiveGroups(G):
	scc = StronglyConnectedComponents(G)
	out = {}
	for g in scc:
		if isSCC(g):
			s = frozenset(g)
			for n in g:
				out[n] = s
	return out

class ReadModifyInfo(object):
	__slots__ = 'localRead', 'localModify', 'heapRead', 'heapModify'
	def __init__(self):
		self.localRead   = set()
		self.localModify = set()
		self.heapRead    = set()
		self.heapModify  = set()

	def accumulate(self, other):
		self.localRead.update(other.localRead)
		self.localModify.update(other.localModify)
		self.heapRead.update(other.heapRead)
		self.heapModify.update(other.heapModify)

class FindMergeSplit(TypeDispatcher):
	@dispatch(ast.Existing, type(None))
	def visitJunk(self, node, info):
		pass

	@dispatch(ast.Local)
	def visitLocal(self, node, info):
		info.localRead.add(node)

	@dispatch(list)
	def visitOther(self, node, *args):
		for child in node:
			self(child, *args)

	@dispatch(ast.Allocate)
	def visitAllocate(self, node, info):
		# TODO null fields?
		pass

	@dispatch(ast.DirectCall)
	def visitDirectCall(self, node, info):
		self(node.selfarg, info)
		self(node.args, info)
		self(node.kwds, info)
		self(node.vargs, info)
		self(node.kargs, info)

	@dispatch(ast.Assign)
	def visitAssign(self, node):
		info = ReadModifyInfo()

		self(node.expr, info)

		info.localModify.update(node.lcls)

		self.lut[node] = info
		return info

	@dispatch(ast.Suite)
	def visitSuite(self, node):
		info = ReadModifyInfo()
		for block in node.blocks:
			info.accumulate(self(block))

		self.lut[node] = info
		return info

	@dispatch(ast.For)
	def visitFor(self, node):
		info = ReadModifyInfo()
		self(node.loopPreamble)
		info.localRead.add(node.iterator)
		info.localModify.add(node.index)
		self(node.bodyPreamble)
		self(node.body)
		self(node.else_)

		self.lut[node] = info
		return info

	def processCode(self, node):
		self.lut = {}
		self(node.ast)

from util.canonical import CanonicalObject

class LocalName(CanonicalObject):
	def __init__(self, local, context):
		self.local   = local
		self.context = context
		self.setCanonical(local, context)

	def isUnique(self):
		return True

class FieldName(CanonicalObject):
	def __init__(self, obj, field, context, unique):
		self.obj     = obj
		self.field   = field
		self.context = context
		self.unique  = unique
		self.setCanonical(obj, field, context, unique)

	def isUnique(self):
		return self.unique

#class CanonicalManager(object):
#	def __init__(self):
#		self.cache = {}

#	def local(self, lcl, context):
#		name = LocalName(lcl, context)
#		return self.cache.setdefault(name, name)

#	def field(self, obj, field, context, unique):
#		name = FieldName(obj, field, context, unique)
#		if not name in self.cache:
#			self.cache[name] = name
#			self.index[(obj, field)].add(name)
#		else:
#			name = self.cache[name]

#		return name


class Enviornment(object):
	def __init__(self, parent):
		self.parent = parent
		self.env = {}
		self.defered = False


class BuildDataflowNetwork(TypeDispatcher):
	def __init__(self):
		self.fms = FindMergeSplit()

		self.contexts = 0
		self.contextLUT = {}

		self.constraints = 0

		self.loopLevel = 0

		self.loopAllocated   = set()
		self.uniqueAllocated = set()

		self.currentContext = ()
		self.contextStack   = []

	def pushContext(self, op):
		self.contextStack.append(self.currentContext)
		self.currentContext += (id(op),)

	def popContext(self):
		self.currentContext = self.contextStack.pop()

	@dispatch(ast.Allocate)
	def visitAllocate(self, node):
		if self.loopLevel:
			dst = self.loopAllocated
		else:
			dst = self.uniqueAllocated

		for obj in node.annotation.allocates[0]:
			dst.add(obj)
			#dst.add((obj, self.currentContext))

		self.constraints += 1

	@dispatch(ast.Load, ast.Store, ast.Check, ast.Return)
	def visitTrack(self, node):
		self.constraints += 1

	@dispatch(ast.Local, ast.Existing)
	def visitTerminal(self, node):
		pass

	@dispatch(ast.DirectCall)
	def visitDirectCall(self, node):
		targets = set()
		for code, context in node.annotation.invokes[0]:
			targets.add(code)

		self.pushContext(node)
		for target in targets:
			self.processCode(target)
		self.popContext()

		self.constraints += 1

	@dispatch(str, ast.CodeParameters)
	def visitLeaf(self, node):
		pass

	@dispatch(ast.Suite, list, tuple, ast.Switch, ast.Condition, ast.Assign, ast.Discard)
	def visitOK(self, node):
		visitAllChildren(self, node)

	@dispatch(ast.For, ast.While)
	def visitFor(self, node):
		# TODO evalute preample outside "loopLevel"
		self.loopLevel += 1
		visitAllChildren(self, node)
		self.loopLevel -= 1

	def processCode(self, node):
		#lut = self.fms.processCode(node)

		self.contexts += 1
		if node not in self.contextLUT:
			self.contextLUT[node] = 1
		else:
			self.contextLUT[node] += 1

		for child in node.children():
			self(child)




class Operation(object):
	def __init__(self, op, targets):
		self.op = op
		self.targets = targets

		self.uses = []
		self.defs = []

		self.heapuses = []
		self.heapdefs = []

class Slot(object):
	def __init__(self, name):
		self.name = name
		self.externalDefinition = False
		self.defs = []
		self.uses = []

	def addUse(self, op):
		self.uses.append(op)
		op.uses.append(self)

	def addDef(self, op):
		assert not self.externalDefinition
		self.defs.append(op)
		op.defs.append(self)

	def __repr__(self):
		return "Slot(%r/%d)" % (self.name, id(self))


class HeapSlot(object):
	def __init__(self, name):
		self.name = name
		self.externalDefinition = False
		self.defs = []
		self.uses = []

	def addUse(self, op):
		self.uses.append(op)
		op.heapuses.append(self)

	def addDef(self, op):
		assert not self.externalDefinition
		self.defs.append(op)
		op.heapdefs.append(self)

	def __repr__(self):
		return "HeapSlot(%r/%d)" % (self.name, id(self))


class MarkUses(TypeDispatcher):
	def __init__(self, bcdf):
		self.bcdf = bcdf

	@dispatch(ast.Code, type(None), ast.Existing, str, int)
	def visitJunk(self, node):
		pass

	@dispatch(list, tuple)
	def visitContainer(self, node):
		visitAllChildren(self, node)

	@dispatch(ast.Local)
	def visitLocal(self, node):
		self.bcdf.useLocal(self.op, node)

	def process(self, node):
		self.op = node
		visitAllChildren(self, node)


class BuildCorrelatedDataflow(TypeDispatcher):
	def __init__(self):
		self.markUses = MarkUses(self)

	def getSlot(self, name):
		if name not in self.slots:
			defn = Slot(name)
			defn.externalDefinition = True
			self.slots[name] = defn
		else:
			defn = self.slots[name]
		return defn

	def getHeapSlot(self, name):
		if name not in self.slots:
			defn = HeapSlot(name)
			defn.externalDefinition = True
			self.slots[name] = defn
		else:
			defn = self.slots[name]
		return defn

	def defineOp(self, op, targets):
		assert op not in self.operations
		defn = Operation(op, targets)
		self.operations[op] = defn
		return defn

	def getOp(self, op):
		defn = self.operations[op]
		return defn

	def useLocal(self, op, lcl):
		slot = self.getSlot(lcl)
		slot.addUse(self.getOp(op))

	def markDefs(self, node, targets):
		op = self.getOp(node)
		for target in targets:
			slot = Slot(target)
			self.slots[target] = slot
			slot.addDef(op)

	def markHeapDefUse(self, node):
		op = self.getOp(node)

		# Uses
		for name in node.annotation.reads[0]:
			self.getHeapSlot(name).addUse(op)

		# For weak updates
		# Must be done before the defs, as they will overwrite.
		for name in node.annotation.modifies[0]:
			self.getHeapSlot(name).addUse(op)

		# Defs
		for name in node.annotation.modifies[0]:
			slot = HeapSlot(name)
			self.slots[name] = slot
			slot.addDef(op)


	@dispatch(ast.DirectCall)
	def visitDirectCall(self, node, targets):
		self.defineOp(node, targets)
		self.markUses.process(node)
		self.markDefs(node, targets)
		self.markHeapDefUse(node)

	@dispatch(ast.Load)
	def visitLoad(self, node, targets):
		self.defineOp(node, targets)
		self.markUses.process(node)
		self.markDefs(node, targets)
		self.markHeapDefUse(node)


	@dispatch(ast.Allocate)
	def visitAllocate(self, node, targets):
		self.defineOp(node, targets)
		self.markUses.process(node)
		self.markDefs(node, targets)
		self.markHeapDefUse(node)

	@dispatch(ast.Assign)
	def visitAssign(self, node):
		self(node.expr, node.lcls)

	@dispatch(ast.Return)
	def visitReturn(self, node):
		assert self.returns is None
		self.defineOp(node, [])
		self.returns = [self.useLocal(node, lcl) for lcl in node.exprs]

	@dispatch(ast.Suite, list)
	def visitOK(self, node):
		visitAllChildren(self, node)

	@dispatch(str, ast.CodeParameters)
	def visitLeaf(self, node):
		pass

	def processCode(self, node):
		self.operations  = {}
		self.slots = {}
		self.returns = None

		for child in node.children():
			self(child)

		print node

		for op in self.operations.itervalues():
			#if not isinstance(op.op, ast.Load): continue

			print op.op
			print op.targets

			print "---"
			for use in op.uses:
				print use, use.defs

			print "---"
			for use in op.heapuses:
				print use, use.defs

			print "---"
			for defn in op.defs:
				print defn, defn.uses

			print "---"
			for defn in op.heapdefs:
				print defn, defn.uses
			print
			print


		print


def checkRecursive(compiler):
	liveFunctions, liveInvocations = programculler.findLiveCode(compiler)
	recursive = findRecursiveGroups(liveInvocations)
	return recursive

#def evaluateCode(compiler, code):
#	pass

def evaluate(compiler):
	with compiler.console.scope('fsdf'):

		if checkRecursive(compiler):
			console.output('recursive call detected, cannot analyze')
			return False

		bdfn = BuildDataflowNetwork()

		for code in compiler.interface.entryCode():
			bdfn.processCode(code)

		for code, count in bdfn.contextLUT.iteritems():
			print '\t', code, count
		compiler.console.output('%d contexts' % bdfn.contexts)
		compiler.console.output('%d constraints' % bdfn.constraints)

		print
		print "Loop Allocated"
		for obj in bdfn.loopAllocated:
			print '\t', obj
		print

		print
		print "Unique Allocated"
		for obj in bdfn.uniqueAllocated:
			print '\t', obj


#		bcd = BuildCorrelatedDataflow()
#		for ep in compiler.interface.entryPoint:
#			bcd.processCode(ep.code)

		return True