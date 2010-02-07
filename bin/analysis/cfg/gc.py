from util.typedispatch import *
from . import graph as cfg
from . dfs import CFGDFS

# Kills unreachable CFG nodes

class Logger(TypeDispatcher):
	def __init__(self):
		self.merges = []

	@defaultdispatch
	def default(self, node):
		pass

	@dispatch(cfg.MultiEntryBlock)
	def visitMerge(self, node):
		self.merges.append(node)

def evaluate(compiler, g):
	logger = Logger()
	dfs = CFGDFS(post=logger)
	dfs.process(g.entryTerminal)

	def live(node):
		return node in dfs.processed

	for merge in logger.merges:
		for prev in merge._prev:
			assert isinstance(prev, tuple), merge._prev

		# HACK exposes the internals of merge
		filtered = [prev for prev in merge._prev if live(prev[0])]
		merge._prev = filtered
