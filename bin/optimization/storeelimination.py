from language.python import ast

from analysis.tools import codeOps
import collections

from optimization.rewrite import rewriteAndSimplify


def evaluate(console, extractor, storeGraph, liveCode):
	with console.scope('dead store elimination'):
		live = set()
		stores = collections.defaultdict(list)

		# Analysis pass
		for code in liveCode:
			live.update(code.annotation.codeReads[0])

			for op in codeOps(code):
				live.update(op.annotation.reads[0])
				if isinstance(op, ast.Store):
					stores[code].append(op)

		# Transform pass
		totalEliminated = 0

		for code in liveCode:
			if not code.isStandardCode() or code.annotation.descriptive: continue

			replace = {}
			eliminated = 0

			# Look for dead stores
			for store in stores[code]:
				for modify in store.annotation.modifies[0]:
					if modify in live: break
					if modify.object.leaks: break
				else:
					replace[store] = []
					eliminated += 1

			# Rewrite the code without the dead stores
			if replace:
				console.output('%r %d' % (code, eliminated))
				rewriteAndSimplify(extractor, storeGraph, code, replace)

			totalEliminated += eliminated

		return totalEliminated > 0