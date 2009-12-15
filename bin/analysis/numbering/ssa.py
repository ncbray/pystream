from util.typedispatch import *
from language.python import ast

class ForwardESSA(TypeDispatcher):
	def __init__(self, rm):
		self.rm = rm
		self.uid = 0

		self._current = {}

		self.readLUT  = {}
		self.writeLUT = {}
		self.psedoReadLUT = {}
		self.existing = {}
		self.merges   = {}

		self.returns = []

		self.parent = None

	def newUID(self):
		temp = self.uid
		self.uid = temp + 1
		return temp

	def branch(self, count):
		current = self.popState()
		branches = [dict(current) for i in range(count)]
		return branches

	def setState(self, state):
		assert self._current is None
		self._current = state

	def popState(self):
		old = self._current
		self._current = None
		return old

	def mergeStates(self, states):
		states = [state for state in states if state is not None]

		if len(states) == 0:
			merged = None
		elif len(states) == 1:
			merged = dict(states[0])
		else:
			keys = set()
			for state in states: keys.update(state.iterkeys())

			merged = {}

			for key in keys:
				values = set()
				for state in states:
					values.add(state.get(key, -1))

				if len(values) == 1:
					dstID = values.pop()
				else:
					dstID = self.newUID()
					self.logMerge(key, values, dstID)
				merged[key] = dstID
		self._current = merged

	def current(self, node):
		assert not isinstance(node, int), node
		if isinstance(node, ast.Existing):
			obj = node.object
			if obj not in self.existing:
				uid = self.newUID()
				self.existing[obj] = uid
			else:
				uid = self.existing[obj]
		else:
			uid = self._current.get(node, -1)
		return uid

	def setCurrent(self, node, uid):
		assert not isinstance(node, int), node
		assert isinstance(uid, int), uid
		self._current[node] = uid


	def rename(self, node):
		if node is not None: self.setCurrent(node, self.newUID())

	def renameAll(self, names):
		for name in names:
			self.rename(name)

	def renameModifiedFields(self, node):
		info = self.rm[node]
		self.renameAll(info.fieldModify)

	# Give unique names to all the fields that may be passed in to the function.
	def renameEntryFields(self, node):
		info = self.rm[node]

		killed = self.code.annotation.killed.merged

		for field in info.fieldRead:
			assert not isinstance(field, ast.Local), field
			if field not in self._current and field.object not in killed:
				self.rename(field)

		for field in info.fieldModify:
			assert not isinstance(field, ast.Local), field
			if field not in self._current and field.object not in killed:
				self.rename(field)


	def logRead(self, node, name):
		self.readLUT[(node, name)] = self.current(name)

	def logModify(self, node, name):
		self.writeLUT[(node, name)] = self.current(name)

	def logPsedoRead(self, node, name):
		self.psedoReadLUT[(node, name)] = self.current(name)


	def logReadLocals(self, parent, node):
		assert self.parent == None
		self.parent = parent
		self(node)
		self.parent = None

	# TODO fields from op?
	def logReadFields(self, node):
		info = self.rm[node]

		for field in info.fieldRead:
			self.logRead(node, field)

		# TODO filter by unique?
		for field in info.fieldModify:
			self.logPsedoRead(node, field)

	# TODO fields from op?
	def logModifiedFields(self, node):
		info = self.rm[node]
		for field in info.fieldModify:
			self.logModify(node, field)


	def logEntry(self):
		filtered = {}
		for name, uid in self._current.iteritems():
			if isinstance(name, ast.Local):
				pass # Assumed all locals are parameters
			else:
				# Fields from killed objects could not have been passed from outside.
				obj = name.object
				if obj in self.code.annotation.killed.merged:
					continue

			filtered[name] = uid

		filtered[None] = -1

		self.entry = filtered

	def logExit(self):
		returns = self.returns
		self.returns = []

		self.mergeStates(returns)
		state = self.popState()
		assert state is not None

		filtered = {}
		for name, uid in state.iteritems():
			if isinstance(name, ast.Local):
				if name not in self.returnparams:
					continue
			else:
				if name in self.entry and self.entry[name] == uid:
					# Not modified.
					continue

				# Fields from killed objects will not propagate
				obj = name.object
				if obj in self.code.annotation.killed.merged:
					continue

			filtered[name] = uid

		self.exit = filtered

	def logMerge(self, name, srcIDs, dstID):
		assert isinstance(dstID, int)
		key = (name, dstID)
		if key not in self.merges:
			self.merges[key] = set()
		self.merges[key].update(srcIDs)


	@dispatch(ast.Local, ast.Existing)
	def visitLocalRead(self, node):
		self.logRead(self.parent, node)

	@dispatch(ast.DoNotCare)
	def visitDoNotCare(self, node):
		pass

	@dispatch(ast.Assign)
	def processAssign(self, node):
		self.logReadLocals(node, node.expr)
		self.logReadFields(node)

		if isinstance(node.expr, ast.Local) and len(node.lcls) == 1:
			# Local copy
			target = node.lcls[0]
			self.setCurrent(target, self.current(node.expr))
			self.logModify(node, target)

		else:
			for lcl in node.lcls:
				self.rename(lcl)
				self.logModify(node, lcl)

		self.renameModifiedFields(node)
		self.logModifiedFields(node)

	@dispatch(ast.Discard)
	def processDiscard(self, node):
		self.logReadLocals(node, node.expr)
		self.logReadFields(node)
		self.renameModifiedFields(node)
		self.logModifiedFields(node)

	@dispatch(ast.Store)
	def processStore(self, node):
		self.logReadLocals(node, node.children())
		self.logReadFields(node)
		self.renameModifiedFields(node)
		self.logModifiedFields(node)

	@dispatch(ast.Return)
	def processReturn(self, node):
		self.logReadLocals(node, node.exprs)
		self.logReadFields(node)

		for dst, src in zip(self.returnparams, node.exprs):
			self.setCurrent(dst, self.current(src))
			self.logModify(node, dst)

		self.renameModifiedFields(node)
		self.logModifiedFields(node)

		# Kill the flow
		self.returns.append(self.popState())

#	@dispatch(ast.For)
#	def processFor(self, node):
#		# Only valid without breaks/contiues


#		self(node.loopPreamble)

#		# TODO mark iterator/index?
#		#info.localRead.add(node.iterator)
#		#info.localModify.add(node.index)

#		# TODO is this sound?
#		self(node.bodyPreamble)

#		self.renameModified(node.body)
#		self(node.body)
#		self.renameModified(node.body)

#		self(node.else_)

#	@dispatch(ast.While)
#	def processWhile(self, node):
#		# Only valid without breaks/contiues

#		self.renameModified(node.condition)
#		self.renameModified(node.body)
#		self(node.condition)

#		self.renameModified(node.body)
#		self(node.body)
#		self.renameModified(node.body)

#		self(node.else_)

	@dispatch(ast.Condition)
	def processCondition(self, node):
		self(node.preamble)

	@dispatch(ast.Switch)
	def processSwitch(self, node):
		self(node.condition)

		self.logRead(node, node.condition.conditional)

		tEntry, fEntry = self.branch(2)

		self.setState(tEntry)
		self(node.t)
		tExit = self.popState()

		self.setState(fEntry)
		self(node.f)
		fExit = self.popState()

		self.mergeStates([tExit, fExit])

	@dispatch(ast.TypeSwitch)
	def processTypeSwitch(self, node):
		self.logRead(node, node.conditional)

		branches = self.branch(len(node.cases))
		exits = []

		for case, branch in zip(node.cases, branches):
			self.setState(branch)

			if case.expr:
				if False:
					# Give the expression the same number as the conditional - they are the same.
					# WARNING if this is used, redundant load elimination may cause a precision loss.
					# Basically, loads inside a type switch will likely be more precise that loads outside.
					exprID = self.current(node.conditional)
				else:
					exprID = self.newUID()
				self.setCurrent(case.expr, exprID)
				self.logModify(node, case.expr)

			self(case.body)
			exits.append(self.popState())

		self.mergeStates(exits)

	@dispatch(str, type(None), ast.Code)
	def processLeaf(self, node):
		pass

	@dispatch(ast.Allocate, ast.Load, ast.Check, ast.DirectCall)
	def processOP(self, node):
		node.visitChildren(self)

	@dispatch(ast.Suite)
	def processOK(self, node):
		node.visitChildren(self)

	@dispatch(list, tuple)
	def processContainer(self, node):
		for child in node:
			self(child)

	def renameParam(self, p):
		if isinstance(p, ast.Local):
			self.rename(p)

	def processCode(self, code):
		self.code = code

		self.renameEntryFields(code.ast)

		params = code.codeparameters
		self.returnparams = params.returnparams

		# Init the parameters
		self.renameParam(params.selfparam)
		for p in (params.params):
			self.renameParam(p)
		assert not hasattr(params, 'kwds')
		self.renameParam(params.vparam)
		self.renameParam(params.kparam)
		# TODO vparam/kparam fields?

		self.logEntry()
		self(code.ast)
		self.logExit()
