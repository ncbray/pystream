from asttools.transform import *
from language.python import ast

from analysis.dataflowIR import graph
from analysis.storegraph import storegraph

import analysis.dataflowIR.dce

class AbstractState(object):
	def __init__(self, predicate):
		self.predicate = predicate
		self.slots = {}

	def freeze(self):
		pass

	def split(self, predicates):
		return [State(predicate, self) for predicate in predicates]

	def get(self, slot):
		if slot not in self.slots:
			result = self.generate(slot)
			self.slots[slot] = result
		else:
			result = self.slots[slot]
		return result

class State(AbstractState):
	def __init__(self, predicate, parent):
		AbstractState.__init__(self, predicate)
		self.parent    = parent
		self.frozen    = False

		parent.freeze()

	def freeze(self):
		self.frozen = True

	def generate(self, slot):
		return self.parent.get(slot)

	def set(self, slot, value):
		assert not self.frozen
		self.slots[slot] = value

def gate(pred, value):
	gate = graph.Gate()
	gate.setPredicate(pred)
	gate.addRead(value)

	result = value.duplicate()
	gate.addModify(result)
	result = gate.modify

	return result

def gatedMerge(pairs):
	if len(pairs) == 1:
		pred, value = pairs[0]
		result = gate(pred, value)
	else:
		m = graph.Merge()

		result = pairs[0][1].duplicate()
		m.modify = result.addDefn(m)

		for pred, value in pairs:
			# Create the gate
			temp = gate(pred, value)

			# Merge the gate
			m.addRead(temp)

		result = m.modify

	return result

class DeferedMerge(AbstractState):
	def __init__(self, predicate, states):
		AbstractState.__init__(self, predicate)
		self.states = states

	def generate(self, slot):
		slots = [state.get(slot) for state in self.states]
		unique = set(slots)
		if len(unique) == 1:
			return unique.pop()

		pairs = [(state.predicate, state.get(slot)) for state in self.states]
		return gatedMerge(pairs)

class DeferedEntryPoint(AbstractState):
	def __init__(self, predicate, code, dataflow):
		AbstractState.__init__(self, predicate)
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
				field = graph.FieldNode()
				field.name = slot
				self.dataflow.entry.addEntry(slot, field)
				return field

	def set(self, slot, value):
		self.slots[slot] = value
		self.dataflow.entry.addEntry(slot, value)



class CodeToDataflow(TypeDispatcher):
	def __init__(self, code):
		self.code = code
		self.dataflow = graph.DataflowGraph()

		self.entryState = DeferedEntryPoint(self.dataflow.entryPredicate, self.code, self.dataflow)
		self.current    = State(self.dataflow.entryPredicate, self.entryState)

		self.returns = []

		self.allModified = set()

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
			pairs = [(state.predicate, state.predicate) for state in states]
			predicate = gatedMerge(pairs)

			state = DeferedMerge(predicate, states)
			state = State(predicate, state)

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

	def localTarget(self, lcl):
		if isinstance(lcl, ast.Local):
			node = graph.LocalNode(lcl)
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
			slot = graph.FieldNode(modify)
			self.set(modify, slot)
			g.addModify(modify, slot)


	@dispatch(ast.Allocate)
	def processAllocate(self, node):
		g = graph.GenericOp(node)
		g.setPredicate(self.pred())

		g.addLocalRead(node.expr, self.get(node.expr))

		self.handleMemory(node, g)
		return g

	@dispatch(ast.Load)
	def processLoad(self, node):
		g = graph.GenericOp(node)
		g.setPredicate(self.pred())

		g.addLocalRead(node.expr, self.get(node.expr))
		g.addLocalRead(node.name, self.get(node.name))

		self.handleMemory(node, g)
		return g


	@dispatch(ast.DirectCall)
	def processDirectCall(self, node):
		g = graph.GenericOp(node)
		g.setPredicate(self.pred())

		if node.selfarg:
			g.addLocalRead(node.selfarg, self.get(node.selfarg))

		for arg in node.args:
			g.addLocalRead(arg, self.get(arg))

		if node.vargs:
			g.addLocalRead(node.vargs, self.get(node.vargs))

		if node.kargs:
			g.addLocalRead(node.kargs, self.get(node.kargs))

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
		g = graph.GenericOp(node)
		g.setPredicate(self.pred())

		g.addLocalRead(node.expr, self.get(node.expr))
		g.addLocalRead(node.name, self.get(node.name))
		g.addLocalRead(node.value, self.get(node.value))

		self.handleMemory(node, g)
		return g

	@dispatch(ast.Return)
	def processReturn(self, node):
		for dst, src in zip(self.code.codeparameters.returnparams, node.exprs):
			self.set(dst, self.get(src))
		self.returns.append(self.popState())

	@dispatch(ast.TypeSwitch)
	def processTypeSwitch(self, node):

		g = graph.GenericOp(node)
		g.setPredicate(self.pred())

		g.addLocalRead(node.conditional, self.get(node.conditional))

		for i in range(len(node.cases)):
			p = graph.PredicateNode(i)
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

		self.dataflow.exit.setPredicate(self.pred())

		for name in self.allModified:
			if isinstance(name, ast.Local):
				if name in self.code.codeparameters.returnparams:
					self.dataflow.exit.addExit(name, state.get(name))
			elif isinstance(name, storegraph.SlotNode):
				if name.object not in killed:
					self.dataflow.exit.addExit(name, state.get(name))

	def setParameter(self, param):
		if param is None: return
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