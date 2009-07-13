from __future__ import absolute_import

import language.python.ast as ast

from util.python import opnames

class SSADefinitions(object):
	def __init__(self):
		self.defn = {}

	def define(self, local, defn, merge=False):
		assert not local in self.defn, "Attempt to redefine %r" % local
		assert local != defn

		defn = constify(defn)

		# Reach for the definition
		while defn in self.defn:
			assert defn != self.defn[defn]
			defn = self.defn[defn]

		self.defn[local] = defn

		#print local, "->", defn
		return local

	def reachTrivial(self, expr):
		defn = self.definition(expr)

		if defn.isReference():
			return defn
		else:
			return expr

	def definition(self, local):
		#assert isinstance(local, ast.Local), local
		return self.defn.get(local, local)

def constify(node):
	return node

def emitInstruction(op, instructions, merge=False):
	assert isinstance(op, ast.SimpleStatement), op
	instructions.append(op)