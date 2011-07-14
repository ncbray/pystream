# Copyright 2011 Nicholas Bray
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from language.python import ast

from analysis.tools import codeOps
import collections

from optimization import rewrite

def evaluate(compiler, prgm, simplify=False):
	with compiler.console.scope('dead store elimination'):
		live = set()
		stores = collections.defaultdict(list)

		# Analysis pass
		for code in prgm.liveCode:
			live.update(code.annotation.codeReads[0])

			for op in codeOps(code):
				live.update(op.annotation.reads[0])
				if isinstance(op, ast.Store):
					stores[code].append(op)

		# Transform pass
		totalEliminated = 0

		for code in prgm.liveCode:
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
				compiler.console.output('%r %d' % (code, eliminated))

				if simplify:
					rewrite.rewriteAndSimplify(compiler, prgm, code, replace)
				else:
					rewrite.rewrite(compiler, code, replace)

			totalEliminated += eliminated

		return totalEliminated > 0
