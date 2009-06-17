from util.typedispatch import *
from language.python import ast

class ForwardESSA(TypeDispatcher):
	def __init__(self, rm):
		self.rm = rm
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

	def processCode(self, code):
		self.updateRead(code.ast)
		self(code.ast)
