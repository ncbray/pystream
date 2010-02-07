from util.typedispatch import *
from language.chameleon import ast, cfg
from . dfs import CFGDFS

class StateInserter(TypeDispatcher):
	def __init__(self):
		self.states = []

	@dispatch(cfg.Entry, cfg.Merge)
	def visitIgnore(self, node):
		pass

	@dispatch(cfg.Switch, cfg.Yield, cfg.Suite)
	def visitOK(self, node):
		if isinstance(node.prev, (cfg.Entry, cfg.Yield, cfg.Merge)):
			state = cfg.State(len(self.states))
			self.states.append(state)
			node.redirectEntries(state)
			state.setExit('normal', node)

	@dispatch(cfg.Exit)
	def visitExit(self, node):
		pass

def evaluate(compiler, g):
	inserter = StateInserter()
	dfs = CFGDFS(pre=inserter)
	dfs.process(g.entryTerminal)
	return inserter.states
