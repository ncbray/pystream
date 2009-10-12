from asttools.transform import *
from language.python import ast

from analysis.dataflowIR import graph
from analysis.storegraph import storegraph

import analysis.dataflowIR.dce

class AbstractState(object):
	def __init__(self, hyperblock, predicate):
		assert predicate.hyperblock is hyperblock
		self.hyperblock = hyperblock
		self.predicate = predicate
		self.slots = {}

	def freeze(self):
		pass

	def split(self, predicates):
		return [State(self.hyperblock, predicate, self) for predicate in predicates]

	def get(self, slot):
		if slot not in self.slots:
			result = self.generate(slot)
			self.slots[slot] = result
		else:
			result = self.slots[slot]
		return result

class State(AbstractState):
	def __init__(self, hyperblock, predicate, parent):
		AbstractState.__init__(self, hyperblock, predicate)
		self.parent    = parent
		self.frozen    = False

		assert self.parent.hyperblock is self.hyperblock

		parent.freeze()

	def freeze(self):
		self.frozen = True

	def generate(self, slot):
		return self.parent.get(slot)

	def set(self, slot, value):
		assert not self.frozen
		self.slots[slot] = value

def gate(pred, value):
	gate = graph.Gate(pred.hyperblock)
	gate.setPredicate(pred)
	gate.addRead(value)

	result = value.duplicate()
	gate.addModify(result)
	result = gate.modify

	return result

def gatedMerge(hyperblock, pairs):
	if len(pairs) == 1:
		assert False, "single gated merge?"
		pred, value = pairs[0]
		result = gate(pred, value)
	else:
		m = graph.Merge(hyperblock)

		result = pairs[0][1].duplicate()
		result.hyperblock = hyperblock
		m.modify = result.addDefn(m)

		for pred, value in pairs:
			# Create the gate
			# TODO will the predicate always have the right hyperblock?
			temp = gate(pred, value)

			# Merge the gate
			m.addRead(temp)

		result = m.modify

	return result

class DeferedMerge(AbstractState):
	def __init__(self, hyperblock, predicate, states):
		AbstractState.__init__(self, hyperblock, predicate)
		self.states = states

	def generate(self, slot):
		slots = [state.get(slot) for state in self.states]
		unique = set(slots)
		if len(unique) == 1:
			return unique.pop()

		pairs = [(state.predicate, state.get(slot)) for state in self.states]
		return gatedMerge(self.hyperblock, pairs)

class DeferedEntryPoint(AbstractState):
	def __init__(self, hyperblock, predicate, code, dataflow):
		AbstractState.__init__(self, hyperblock, predicate)
		self.code = code
		self.dataflow = dataflow

	def generate(self, slot):
		if isinstance(slot, ast.Local):
			# Parameters are explicitly set.
			# If it isn't already here, it's an undefined local.
			return self.dataflow.null
		elif isinstance(slot, ast.Existing):
			return self.dataflow.getExisting(slot)
		else:
			# Fields from killed object cannot come from beyond the entry point.
			killed = self.code.annotation.killed.merged
			if slot.object in killed:
				return self.dataflow.null
			else:
				field = graph.FieldNode(self.hyperblock, slot)
				self.dataflow.entry.addEntry(slot, field)
				return field

	def set(self, slot, value):
		self.slots[slot] = value
		self.dataflow.entry.addEntry(slot, value)



class CodeToDataflow(TypeDispatcher):
	def __init__(self, code):
		self.uid = 0
		hyperblock = self.newHyperblock()

		self.code = code
		self.dataflow = graph.DataflowGraph(hyperblock)

		self.entryState = DeferedEntryPoint(hyperblock, self.dataflow.entryPredicate, self.code, self.dataflow)
		self.current    = State(hyperblock, self.dataflow.entryPredicate, self.entryState)

		self.returns = []

		self.allModified = set()

	def newHyperblock(self):
		name = self.uid
		self.uid += 1
		return graph.Hyperblock(name)

	def branch(self, predicates):
		current = self.popState()
		branches = current.split(predicates)
		return branches

	def setState(self, state):
		assert self.current is None
		self.current = state

	def popState(self):
		old = self.current
		self.current = None
		return old

	def mergeStates(self, states):
		# TODO predicated merge / mux?
		states = [state for state in states if state is not None]

		if len(states) == 1:
			# TODO is this sound?  Does it interfere with hyperblock definition?
			state = states.pop()
		else:
			# TODO only create a new hyperblock when merging from different hyperblocks?
			hyperblock = self.newHyperblock()
			pairs = [(state.predicate, state.predicate) for state in states]
			predicate = gatedMerge(hyperblock, pairs)
			predicate.name = repr(hyperblock)

			state = DeferedMerge(hyperblock, predicate, states)
			state = State(hyperblock, predicate, state)

		self.setState(state)
		return state


	def get(self, slot):
		return self.current.get(slot)

	def set(self, slot, value):
		value.addName(slot)
		self.allModified.add(slot)
		return self.current.set(slot, value)

	def pred(self):
		return self.current.predicate

	def hyperblock(self):
		return self.current.hyperblock

	def localTarget(self, lcl):
		if isinstance(lcl, ast.Local):
			node = graph.LocalNode(self.hyperblock(), (lcl,))
		else:
			assert False
		return node

	def handleOp(self, node, targets):
		g = self(node)
		for lcl in targets:
			target = self.localTarget(lcl)
			self.set(lcl, target)
			g.addLocalModify(lcl, target)

	def handleMemory(self, node, g):
		# Reads
		for read in node.annotation.reads.merged:
			slot = self.get(read)
			g.addRead(read, slot)

		# Psedo reads
		for modify in node.annotation.modifies.merged:
			slot = self.get(modify)
			g.addPsedoRead(modify, slot)

		# Modifies
		for modify in node.annotation.modifies.merged:
			slot = graph.FieldNode(self.hyperblock(), modify)
			self.set(modify, slot)
			g.addModify(modify, slot)

	def localRead(self, g, lcl):
		if isinstance(lcl, (ast.Local, ast.Existing)):
			g.addLocalRead(lcl, self.get(lcl))

	@dispatch(ast.Allocate)
	def processAllocate(self, node):
		g = graph.GenericOp(self.hyperblock(), node)
		g.setPredicate(self.pred())

		self.localRead(g, node.expr)

		self.handleMemory(node, g)
		return g

	@dispatch(ast.Load)
	def processLoad(self, node):
		g = graph.GenericOp(self.hyperblock(), node)
		g.setPredicate(self.pred())

		self.localRead(g, node.expr)
		self.localRead(g, node.name)

		self.handleMemory(node, g)
		return g


	@dispatch(ast.DirectCall)
	def processDirectCall(self, node):
		g = graph.GenericOp(self.hyperblock(), node)
		g.setPredicate(self.pred())

		self.localRead(g, node.selfarg)

		for arg in node.args:
			self.localRead(g, arg)

		self.localRead(g, node.vargs)
		self.localRead(g, node.kargs)


		self.handleMemory(node, g)
		return g


	@dispatch(ast.Local, ast.Existing)
	def visitLocalRead(self, node):
		return self.get(node)

	@dispatch(ast.Assign)
	def processAssign(self, node):
		if isinstance(node.expr, ast.Local) and len(node.lcls) == 1:
			# Local copy
			target = node.lcls[0]
			g = self.get(node.expr)
			self.set(target, g)

		else:
			self.handleOp(node.expr, node.lcls)

	@dispatch(ast.Discard)
	def processDiscard(self, node):
		self.handleOp(node.expr, [])

	@dispatch(ast.Store)
	def processStore(self, node):
		g = graph.GenericOp(self.hyperblock(), node)
		g.setPredicate(self.pred())

		self.localRead(g, node.expr)
		self.localRead(g, node.name)
		self.localRead(g, node.value)

		self.handleMemory(node, g)
		return g

	@dispatch(ast.Return)
	def processReturn(self, node):
		for dst, src in zip(self.code.codeparameters.returnparams, node.exprs):
			self.set(dst, self.get(src))
		self.returns.append(self.popState())

	@dispatch(ast.TypeSwitch)
	def processTypeSwitch(self, node):

		g = graph.GenericOp(self.hyperblock(), node)
		g.setPredicate(self.pred())

		self.localRead(g, node.conditional)

		for i in range(len(node.cases)):
			p = graph.PredicateNode(self.hyperblock(), i)
			g.predicates.append(p.addDefn(g))
		branches = self.branch(g.predicates)
		exits = []

		for case, branch in zip(node.cases, branches):
			self.setState(branch)
			if case.expr:
				target = self.localTarget(case.expr)
				self.set(case.expr, target)
			else:
				target = None
			g.addLocalModify(case.expr, target)

			self(case.body)
			exits.append(self.popState())

		self.mergeStates(exits)

	@dispatch(str, type(None), ast.Code)
	def processLeaf(self, node):
		return None

	@dispatch(ast.Suite, list, tuple)
	def processOK(self, node):
		visitAllChildren(self, node)

	def handleExit(self):
		state = self.mergeStates(self.returns)

		killed = self.code.annotation.killed.merged

		self.dataflow.exit = graph.Exit(state.hyperblock)
		self.dataflow.exit.setPredicate(state.predicate)

		for name in self.allModified:
			if isinstance(name, ast.Local):
				if name in self.code.codeparameters.returnparams:
					self.dataflow.exit.addExit(name, state.get(name))
			elif isinstance(name, storegraph.SlotNode):
				if name.object not in killed:
					self.dataflow.exit.addExit(name, state.get(name))

	def setParameter(self, param):
		if isinstance(param, ast.Local):
			g = self.localTarget(param)
			self.entryState.set(param, g)

	def processCode(self):
		# Init the parameters
		params = self.code.codeparameters
		self.setParameter(params.selfparam)
		for p in (params.params):
			self.setParameter(p)
		assert not hasattr(params, 'kwds')
		self.setParameter(params.vparam)
		self.setParameter(params.kparam)

		self(self.code.ast)

		self.handleExit()

		return self.dataflow


def evaluateCode(compiler, code):
	ctd = CodeToDataflow(code)
	dataflow = ctd.processCode()
	analysis.dataflowIR.dce.evaluateDataflow(dataflow)
	return dataflow