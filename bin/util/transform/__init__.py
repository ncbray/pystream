from base import *
from . generictraversal import All, Congruence
from . dynamic import DynamicRule, DynScope, DynCopy, DynRestore, DynIntersect, DynDefine, DynUndefine
from . enviornment import Enviornment

from . pattern import Match, Build

from derived import *


def limit(s, length):
	if len(s) > length:
		s = s[:length-3]+"..."
	return s

class Debug(Transformer):
	__metaclass__ = astnode
	__fields__    = 's'
	__types__     = {'s':Transformer}

	def __call__(self, node, env):
		result = self.s(node, env)

		if result != fail:
			print "<<<", limit(repr(self.s), 70)
			print repr(node)
			print repr(result)
			print

		return result

	def __repr__(self):
		return repr(self.s)
