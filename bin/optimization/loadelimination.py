from language.python import ast

from analysis.numbering.readmodify import FindReadModify
from analysis.numbering.dominance import MakeForwardDominance
from analysis.numbering.ssa import ForwardESSA

from optimization.rewrite import rewriteAndSimplify

# For debugging
from util.io.xmloutput import XMLOutput

import collections


class RedundantLoadEliminator(object):
	def __init__(self, compiler, prgm, readNumbers, writeNumbers, dom):
		self.compiler     = compiler
		self.prgm         = prgm
		self.readNumbers  = readNumbers
		self.writeNumbers = writeNumbers
		self.dom = dom

		self.eliminated = 0

	def readNumber(self, node, arg):
		if isinstance(arg, ast.Existing):
			return 0
		else:
			return self.readNumbers[(node, arg)]

	def writeNumber(self, node, arg):
		return self.writeNumbers[(node, arg)]

	def dominates(self, a, b):
		adom = self.dom[a]
		bdom = self.dom[b]
		return adom[0] < bdom[0] and adom[1] > bdom[1]

	def findLoadStores(self):
		loads  = set()
		stores = set()

		# HACK to find all the interesting nodes.
		# TODO use existing code?
		for (node, src), number in self.readNumbers.iteritems():
			if isinstance(node, ast.Assign) and isinstance(node.expr, ast.Load):
				loads.add(node)

			if isinstance(node, ast.Store):
				stores.add(node)

		return loads, stores

	def makeReadSig(self, op, arg):
		if isinstance(arg, ast.Existing):
			sig = arg.object
		elif isinstance(arg, ast.Local):
			# Dropping the arg from the signature allows load elimination across must-aliases
			#sig = (arg, self.readNumber(op, arg))
			sig = self.readNumber(op, arg)
		else:
			assert False, arg
		return sig


	def generateSignature(self, op, node, signatures):
		exprSig = self.makeReadSig(op, node.expr)
		nameSig = self.makeReadSig(op, node.name)

		if isinstance(node, ast.Load):
			fields = [(field, self.readNumber(op, field)) for field in node.annotation.reads[0]]
		elif isinstance(node, ast.Store):
			fields = [(field, self.writeNumber(op, field)) for field in node.annotation.modifies[0]]
		else:
			assert False, node

		sig = (exprSig, node.fieldtype, nameSig, frozenset(fields))

		signatures[sig].append(op)


	def generateSignatures(self, code):
		loads, stores = self.findLoadStores()
		signatures  = collections.defaultdict(list)

		for op in loads:  self.generateSignature(op, op.expr, signatures)
		for op in stores: self.generateSignature(op, op, signatures)

		return signatures

	def getReplacementSource(self, dominator):
		if dominator not in self.newName:
			if isinstance(dominator, ast.Store):
				old = dominator.value
			else:
				assert len(dominator.lcls) == 1
				old = dominator.lcls[0]

			if isinstance(old, ast.Existing):
				src = ast.Existing(old.object)
			else:
				src = ast.Local(old.name)
				self.replace[dominator] = [dominator, ast.Assign(old, [src])]

			src.annotation = old.annotation
			self.newName[dominator] = src
		else:
			src = self.newName[dominator]
		return src

	def dominatorSubtree(self, loads):
		# HACK n^2 for find the absolute dominator....
		dom = {}

		for load in loads:
			dom[load] = load

		for test in loads:
			for load, dominator in dom.iteritems():
				if self.dominates(test, dominator):
					dom[load] = test
		return dom

	def generateReplacements(self, signatures):
		self.newName = {}
		self.replace = {}

		for sig, loads in signatures.iteritems():
			if len(loads) > 1:
				dom = self.dominatorSubtree(loads)

				for op, dominator in dom.iteritems():
					if op is not dominator:
						assert not isinstance(op, ast.Store)
						assert len(op.lcls) == 1

						src = self.getReplacementSource(dominator)
						self.replace[op] = ast.Assign(src, [op.lcls[0]])
						self.eliminated += 1
		return self.replace

	def processCode(self, code):
		signatures = self.generateSignatures(code)
		replace = self.generateReplacements(signatures)

		rewriteAndSimplify(self.compiler, self.prgm, code, replace)
		return self.eliminated


def evaluateCode(compiler, prgm, code):
	rm = FindReadModify().processCode(code)

	dom = MakeForwardDominance().processCode(code)

	fessa = ForwardESSA(rm)
	fessa.processCode(code)

	rle = RedundantLoadEliminator(compiler, prgm, fessa.readLUT, fessa.writeLUT, dom)
	eliminated = rle.processCode(code)
	if eliminated:
		print '\t', code, eliminated

def evaluate(compiler, prgm):
	with compiler.console.scope('redundant load elimination'):
		for code in prgm.liveCode:
			if code.isStandardCode() and not code.annotation.descriptive:
				evaluateCode(compiler, prgm, code)
