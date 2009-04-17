from util.typedispatch import *
from language.python import ast
from language.base.metaast import children

from util.xform.traversal import visitAllChildrenArgs, replaceAllChildren

import util.graphalgorithim.dominator

import collections

from util.xmloutput import XMLOutput

class ReadModifyInfo(object):
	__slots__ = 'localRead', 'localModify', 'fieldRead', 'fieldModify'

	def __init__(self):
		self.localRead   = set()
		self.localModify = set()
		self.fieldRead   = set()
		self.fieldModify = set()

	def update(self, other):
		self.localRead.update(other.localRead)
		self.localModify.update(other.localModify)
		self.fieldRead.update(other.fieldRead)
		self.fieldModify.update(other.fieldModify)


class FindReadModify(StrictTypeDispatcher):

	def getInfo(self, node):
		info = ReadModifyInfo()
		for child in children(node):
			info.update(self(child))
		return info

	@dispatch(ast.Existing, ast.Code, type(None), str)
	def visitLeaf(self, node, info):
		pass

	@dispatch(ast.Local)
	def visitLocal(self, node, info):
		info.localRead.add(node)

	@dispatch(ast.Allocate)
	def visitAllocate(self, node, info):
		# TODO what about type/field nullification?
		visitAllChildrenArgs(self, node, info)

	@dispatch(ast.Load, ast.Check)
	def visitMemoryExpr(self, node, info):
		visitAllChildrenArgs(self, node, info)
		info.fieldRead.update(node.annotation.reads[0])
		info.fieldModify.update(node.annotation.modifies[0])

	@dispatch(ast.Store)
	def visitStore(self, node):
		info = ReadModifyInfo()
		visitAllChildrenArgs(self, node, info)
		info.fieldRead.update(node.annotation.reads[0])
		info.fieldModify.update(node.annotation.modifies[0])
		self.lut[node] = info
		return info


	@dispatch(ast.DirectCall)
	def visitDirectCall(self, node, info):
		visitAllChildrenArgs(self, node, info)
		info.fieldRead.update(node.annotation.reads[0])
		info.fieldModify.update(node.annotation.modifies[0])

	@dispatch(ast.Assign)
	def visitAssign(self, node):
		info = ReadModifyInfo()
		self(node.expr, info)
		info.localModify.update(node.lcls)
		self.lut[node] = info
		return info

	@dispatch(ast.Return)
	def visitReturn(self, node):
		info = ReadModifyInfo()
		self(node.exprs, info)
		self.lut[node] = info
		return info

	@dispatch(ast.Discard)
	def visitDiscard(self, node):
		info = ReadModifyInfo()
		self(node.expr, info)
		self.lut[node] = info
		return info

	@dispatch(list)
	def visitList(self, node, info):
		visitAllChildrenArgs(self, node, info)

	@dispatch(ast.Suite)
	def visitSuite(self, node):
		info = self.getInfo(node.blocks)
		self.lut[node] = info
		return info

	@dispatch(ast.For)
	def visitFor(self, node):
		info = ReadModifyInfo()
		info.update(self(node.loopPreamble))
		info.localRead.add(node.iterator)
		info.localModify.add(node.index)

		info.update(self(node.bodyPreamble))
		info.update(self(node.body))
		info.update(self(node.else_))

		self.lut[node] = info
		return info


	@dispatch(ast.Condition)
	def visitCondition(self, node):
		info = ReadModifyInfo()
		info.update(self(node.preamble))
		info.localRead.add(node.conditional)
		self.lut[node] = info
		return info


	@dispatch(ast.While)
	def visitWhile(self, node):
		info = ReadModifyInfo()
		info.update(self(node.condition))
		info.update(self(node.body))
		info.update(self(node.else_))
		self.lut[node] = info
		return info

	@dispatch(ast.Switch)
	def visitSwitch(self, node):
		info = ReadModifyInfo()
		info.update(self(node.condition))
		info.update(self(node.t))
		info.update(self(node.f))
		self.lut[node] = info
		return info

	def processCode(self, code):
		self.lut = {}
		self(code.ast)
		return self.lut

class ForwardDataflow(StrictTypeDispatcher):

	def makeSymbolic(self, node):
		entry = (node, 'entry')
		exit  = (node, 'exit')

		self.entry[node] = entry
		self.exit[node] = exit

		return entry, exit

	def makeConcrete(self, node):
		entry = node
		exit  = node
		self.entry[node] = entry
		self.exit[node] = exit
		return entry, exit

	def link(self, prev, next):
		self._link(self.exit[prev], self.entry[next])

	def _link(self, prev, next):
		if prev is not None:
			self.next[prev].append(next)


	@dispatch(ast.Assign, ast.Discard, ast.Store)
	def visitStatement(self, node):
		entry, exit = self.makeConcrete(node)

	@dispatch(ast.Return)
	def visitReturn(self, node):
		self.entry[node] = node
		self.exit[node]  = None

		self._link(node, self.returnExit)

	@dispatch(ast.Condition)
	def visitCondition(self, node):
		# HACKISH?
		entry, exit = self.makeSymbolic(node)

		self(node.preamble)

		self._link(entry, self.entry[node.preamble])
		self._link(self.exit[node.preamble], exit)


	@dispatch(ast.Switch)
	def visitSwitch(self, node):
		entry, exit = self.makeSymbolic(node)

		self(node.condition)
		self(node.t)
		self(node.f)

		self._link(entry, self.entry[node.condition])

		self.link(node.condition, node.t)
		self.link(node.condition, node.f)

		self._link(self.exit[node.t], exit)
		self._link(self.exit[node.f], exit)

	@dispatch(ast.For)
	def visitFor(self, node):
		# HACKISH?

		entry, exit = self.makeSymbolic(node)

		self(node.loopPreamble)
		self(node.bodyPreamble)
		self(node.body)
		self(node.else_)

		self._link(entry, self.entry[node.loopPreamble])
		self.link(node.loopPreamble, node.bodyPreamble)
		self.link(node.bodyPreamble, node.body)
		self.link(node.body, node.bodyPreamble)
		self.link(node.body, node.else_)
		self._link(self.exit[node.else_], exit)

		# Nothing to iterate?
		self.link(node.loopPreamble, node.else_)


	@dispatch(ast.While)
	def visitWhile(self, node):
		# HACKISH?

		entry, exit = self.makeSymbolic(node)

		self(node.condition)
		self(node.body)
		self(node.else_)

		self._link(entry, self.entry[node.condition])
		self.link(node.condition, node.body)
		self.link(node.body, node.condition)
		self.link(node.condition, node.else_)
		self._link(self.exit[node.else_], exit)



	@dispatch(ast.Suite)
	def visitSuite(self, node):
		entry, exit = self.makeSymbolic(node)

		prev = entry
		for child in node.blocks:
			self(child)
			self._link(prev, self.entry[child])
			prev = self.exit[child]

		self._link(prev, exit)

	def processCode(self, code):
		self.next = collections.defaultdict(list)
		self.entry = {}
		self.exit  = {}

		entry, exit = self.makeSymbolic(code)

		self.returnExit = exit

		self(code.ast)

		self._link(entry, self.entry[code.ast])
		self._link(self.exit[code.ast], exit)

		return self.next

class MakeForwardDominance(object):
	def printDebug(self, tree, head):
		f = XMLOutput(open('temp.html', 'w'))
		f.begin('ul')

		def printNode(f, node):
			if not isinstance(node, tuple):
				f.begin('li')
				f.write(str(node))
				f.begin('ul')

			children = tree.get(node, ())

			for child in children:
				printNode(f, child)

			if not isinstance(node, tuple):
				f.end('ul')
				f.end('li')

		printNode(f, head)

		f.end('ul')
		f.close()

	def number(self, node):
		if node in self.processed: return
		self.processed.add(node)

		self.pre[node] = self.uid
		self.uid += 1

		for next in self.G.get(node, ()):
			self.number(next)

		self.dom[node] = (self.pre[node], self.uid)
		self.uid += 1

	def processCode(self, code):
		self.uid  = 0
		self.pre  = {}
		self.dom = {}

		self.processed = set()

		fdf = ForwardDataflow()

		self.G = fdf.processCode(code)
		head = fdf.entry[code]

		tree, idoms = util.graphalgorithim.dominator.dominatorTree(self.G, head)

		#self.printDebug(tree, head)

		self.G = tree
		self.number(head)

#		for key, value in self.dom.iteritems():
#			if not isinstance(key, tuple):
#				print key
#				print value
#				print

		return self.dom


class ForwardESSA(StrictTypeDispatcher):
	def __init__(self, rm, dom):
		self.rm = rm
		self.dom = dom
		self.uid = 0

		self._current = {}

		self.readLUT  = {}
		self.writeLUT = {}

	def newUID(self):
		temp = self.uid
		self.uid = temp + 1
		return temp

	def copyState(self):
		return dict(self._current)

	def restoreState(self, state):
		old = self._current
		self._current = state
		return old

	def current(self, node):
		return self._current[node]

	def updateWritten(self, node):
		info = self.rm[node]
		for lcl in info.localModify:
			self._current[lcl] = self.newUID()

		for field in info.fieldModify:
			self._current[field] = self.newUID()

	def updateRead(self, node):
		info = self.rm[node]
		for lcl in info.localRead:
			self._current[lcl] = self.newUID()

		for field in info.fieldRead:
			self._current[field] = self.newUID()

	def markRead(self, node):
		info = self.rm[node]
		for lcl in info.localRead:
			self.readLUT[(node, lcl)] = self.current(lcl)

		for field in info.fieldRead:
			self.readLUT[(node, field)] = self.current(field)

	def markWritten(self, node):
		info = self.rm[node]
		for lcl in info.localModify:
			self.writeLUT[(node, lcl)] = self.current(lcl)

		for field in info.fieldModify:
			self.writeLUT[(node, field)] = self.current(field)

	@dispatch(ast.Existing)
	def visitLeaf(self, node, parent):
		pass

	@dispatch(ast.Assign, ast.Discard, ast.Store)
	def processAssign(self, node):
		self.markRead(node)
		self.updateWritten(node)
		self.markWritten(node)

	@dispatch(ast.Return)
	def processReturn(self, node):
		self.markRead(node)
		self.updateWritten(node)
		self.markWritten(node)

		# Kill the flow
		self._current = None

	@dispatch(ast.For)
	def processFor(self, node):
		# Only valid without breaks/contiues


		self(node.loopPreamble)

		# TODO mark iterator/index?
		#info.localRead.add(node.iterator)
		#info.localModify.add(node.index)

		self(node.bodyPreamble)

		self.updateWritten(node.body)
		self(node.body)
		self.updateWritten(node.body)

		self(node.else_)

	@dispatch(ast.While)
	def processWhile(self, node):
		# Only valid without breaks/contiues

		self.updateWritten(node.condition)
		self.updateWritten(node.body)
		self(node.condition)

		self.updateWritten(node.body)
		self(node.body)
		self.updateWritten(node.body)

		self(node.else_)

	@dispatch(ast.Condition)
	def processCondition(self, node):
		self(node.preamble)
		# TODO conditional?

	@dispatch(ast.Switch)
	def processSwitch(self, node):
		self(node.condition)

		backup = self.copyState()
		self(node.t)

		tExit = self.restoreState(backup)
		self(node.f)
		fExit = self._current

		if tExit is not None and fExit is not None:

			self.updateWritten(node.t)
			self.updateWritten(node.f)
		elif tExit is not None:
			self._current = tExit
		elif fExit is not None:
			self._current = fExit

	@dispatch(ast.Suite, list)
	def processOK(self, node):
		visitAllChildren(self, node)

	def readNumber(self, node, arg):
		if isinstance(arg, ast.Existing):
			return 0
		else:
			return self.readLUT[(node, arg)]

	def writeNumber(self, node, arg):
		return self.writeLUT[(node, arg)]

	def processCode(self, code):
		self.updateRead(code.ast)
		info = self.rm[code.ast]


		self(code.ast)

		self.findRedundancies(code)


	def findRedundancies(self, code):
		loads  = set()
		stores = set()
		checks = set()

		for (node, src), number in self.readLUT.iteritems():
			if isinstance(node, ast.Assign) and isinstance(node.expr, ast.Load):
				loads.add(node)

			if isinstance(node, ast.Store):
				stores.add(node)

			if isinstance(node, ast.Check):
				checks.add(node)


		loadSig  = collections.defaultdict(list)
		storeSig = collections.defaultdict(list)

		def makeReadSig(op, arg):
			if isinstance(arg, ast.Existing):
				(arg.object, 0)
			else:
				return (arg, self.readNumber(op, arg))

		for op in loads:
			load = op.expr

			exprSig = makeReadSig(op, load.expr)
			nameSig = makeReadSig(op, load.name)

			fields = [(field, self.readNumber(op, field)) for field in load.annotation.reads[0]]
			sig = (exprSig, load.fieldtype, nameSig, frozenset(fields))

			loadSig[sig].append(op)


		for store in stores:
			exprSig = makeReadSig(store, store.expr)
			nameSig = makeReadSig(store, store.name)
			fields = [(field, self.writeNumber(store, field)) for field in store.annotation.modifies[0]]
			sig = (exprSig, store.fieldtype, nameSig, frozenset(fields))

			loadSig[sig].append(store)

		newName = {}
		replace = {}

		for sig, loads in loadSig.iteritems():
			if len(loads) > 1:
				# HACK n^2 for find the absolute dominator....
				dom = {}
				for load in loads:
					dom[load] = load
				for test in loads:
					for load, dominator in dom.iteritems():
						if self.dominates(test, dominator):
							dom[load] = test

				for op, dominator in dom.iteritems():
					if op is not dominator:
						if dominator not in newName:
							if isinstance(dominator, ast.Store):
								old = dominator.value
							else:
								assert len(dominator.lcls) == 1
								old = dominator.lcls[0]
							lcl = ast.Local(old.name)
							lcl.annotation = old.annotation
							newName[dominator] = lcl
							replace[dominator] = [dominator, ast.Assign(old, [lcl])]
						else:
							lcl = newName[dominator]

						assert not isinstance(op, ast.Store)
						assert len(op.lcls) == 1
						replace[op] = ast.Assign(lcl, [op.lcls[0]])

		if replace:
			Replacer().processCode(code, replace)


	def dominates(self, a, b):
		adom = self.dom[a]
		bdom = self.dom[b]
		return adom[0] < bdom[0] and adom[1] > bdom[1]

class Replacer(StrictTypeDispatcher):
	@defaultdispatch
	def visitOK(self, node):
		if node in self.replaced:
			return node

		# Prevent stupid recursion, where the replacement contains the original.
		isreplaced = node in self.replacements
		if isreplaced:
			oldnode = node
			self.replaced.add(oldnode)
			node = self.replacements[node]

		node = allChildren(self, node)

		if isreplaced:
			self.replaced.remove(oldnode)

		return node

	@dispatch(list)
	def visitUnhashable(self, node):
		return allChildren(self, node)

	def processCode(self, code, replacements):
		self.replacements = replacements
		self.replaced = set()

		assert code.annotation.contexts is not None
		code = replaceAllChildren(self, code)
		assert code.annotation.contexts is not None


def evaluateCode(code):
	print code
	rm = FindReadModify().processCode(code)
	dom = MakeForwardDominance().processCode(code)

	analysis = ForwardESSA(rm, dom)
	analysis.processCode(code)

def evaluate(console, dataflow, entryPoints):
	console.begin('numbering')

	for code, expr, args in entryPoints:
		evaluateCode(code)
	console.end()