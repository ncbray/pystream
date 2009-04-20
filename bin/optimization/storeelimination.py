from language.python import ast

from analysis.tools import codeOps
import collections

from optimization.rewrite import rewriteAndSimplify


def evaluate(console, dataflow, entryPoints):
	console.begin('dead store elimination')

	live = set()
	stores = collections.defaultdict(list)

	# Analysis pass
	for code in dataflow.db.liveCode:
		for op in codeOps(code):
			if isinstance(op, (ast.Load, ast.Check)):
				live.update(op.annotation.reads[0])
			elif isinstance(op, ast.Store):
				stores[code].append(op)

	# Transform pass
	for code in dataflow.db.liveCode:
		if code.annotation.descriptive: continue

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
			rewriteAndSimplify(dataflow, code, replace)

	console.end()