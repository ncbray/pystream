from util.typedispatch import *
from language.python import ast
from . import graph as cfg
from . dfs import CFGDFS

NoNormalFlow = cfg.NoNormalFlow

class OpFlow(TypeDispatcher):
	@dispatch(ast.leafTypes, ast.GetCellDeref, ast.Code, ast.DoNotCare, ast.OutputBlock, ast.InputBlock)
	def visitLeaf(self, node):
		pass

	@dispatch(ast.Existing)
	def visitExisting(self, node):
		pass

	@dispatch(ast.Local)
	def visitLocal(self, node):
		# TODO - undefined variables?
		pass

	def assumePessimistic(self):
		# Pessimistic
		# TODO get info via callback?
		self.errors |= True

	@dispatch(ast.Call, ast.BinaryOp, ast.UnaryPrefixOp, ast.ConvertToBool, ast.DirectCall,
			ast.Is, ast.UnpackSequence,
			ast.GetGlobal, ast.SetGlobal, ast.DeleteGlobal,
			ast.GetAttr, ast.SetAttr, ast.DeleteAttr,
			ast.GetSubscript, ast.SetSubscript, ast.DeleteSubscript,
			ast.Load, ast.Store)
	def visitOp(self, node):
		node.visitChildren(self)
		self.assumePessimistic()


	@dispatch(ast.BuildTuple, ast.Allocate)
	def visitBuildTuple(self, node):
		node.visitChildren(self)
		# No problems

	@dispatch(ast.Return)
	def visitReturn(self, node):
		node.visitChildren(self)
		# No problems


	@dispatch(ast.Discard, ast.Assign)
	def visitOK(self, node):
		node.visitChildren(self)

	def process(self, node):
		self.normal = True
		self.fails  = False
		self.errors = False
		self.yields = False

		try:
			self(node)
		except NoNormalFlow:
			self.normal = False

class FlowKiller(TypeDispatcher):
	def __init__(self, opFlow):
		self.opFlow = opFlow
		self.yields = False

	@dispatch(cfg.Yield)
	def visitYield(self, node):
		self.yields = True

	@dispatch(cfg.Entry, cfg.Exit, cfg.Merge)
	def visitOK(self, node):
		pass

	@dispatch(cfg.Suite)
	def visitSuite(self, node):
		normal = True
		fails  = False
		errors = False

		ops = []
		for op in node.ops:
			self.opFlow.process(op)
			ops.append(op)

			fails  |= self.opFlow.fails
			errors |= self.opFlow.errors
			self.yields |= self.opFlow.yields

			if not self.opFlow.normal:
				normal = False
				break

		node.ops = ops

		if not normal: node.killExit('normal')
		if not fails:  node.killExit('fail')
		if not errors: node.killExit('error')

	@dispatch(cfg.Switch)
	def visitSwitch(self, node):
		self.opFlow.process(node.condition)
		self.yields |= self.opFlow.yields

		if not self.opFlow.normal:
			assert False
			# HACK should convert into a suite?
			node.killExit('t')
			node.killExit('f')

		if not self.opFlow.fails:
			node.killExit('fail')

		if not self.opFlow.errors:
			node.killExit('error')

	@dispatch(cfg.TypeSwitch)
	def visitTypeSwitch(self, node):
		self.yields |= self.opFlow.yields

		if not self.opFlow.normal:
			assert False

		if not self.opFlow.fails:
			node.killExit('fail')

		if not self.opFlow.errors:
			node.killExit('error')

def evaluate(compiler, g):
	dfs  = CFGDFS(post=FlowKiller(OpFlow()))
	dfs.process(g.entryTerminal)
