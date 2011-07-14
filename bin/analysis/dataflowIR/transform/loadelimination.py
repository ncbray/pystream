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

from analysis.dataflowIR import graph
from analysis.dataflowIR import predicate
from analysis.dataflowIR.traverse import dfs

def findLoadSrc(g):
	for node in g.heapReads.itervalues():
		defn = node.canonical().defn
		return defn

# Is the use a copy to the definition?
# It may be filtered by type switches, etc.
def isLocalSubset(defn, use):
	defn = defn.canonical()
	use = use.canonical()

	if defn is use:
		return True
	elif use.defn.isOp() and use.defn.isTypeSwitch():
		conditional = use.defn.op.conditional
		cNode = use.defn.localReads[conditional]
		return isLocalSubset(defn, cNode)

	return False

def attemptTransform(g, pg):
	# Is the load unused or invalid?
	if len(g.localModifies) != 1:
		return False

	defn = findLoadSrc(g)

	if isinstance(defn, graph.GenericOp) and defn.isStore():
		# Make sure the load / store parameters are identical
		# expr
		if not isLocalSubset(defn.localReads[defn.op.expr].canonical(), g.localReads[g.op.expr].canonical()):
			return False

		# field type
		if not g.op.fieldtype == defn.op.fieldtype:
			return False

		# field name
		if not g.localReads[g.op.name].canonical() == defn.localReads[defn.op.name].canonical():
			return False

		# Make sure the store predicate dominates the load predicate
		if not pg.dominates(defn.canonicalpredicate, g.canonicalpredicate):
			return False


		# Make sure the heap read / modify is identical

		reads = frozenset([node.canonical() for node in g.heapReads.itervalues()])
		modifies = frozenset([node.canonical() for node in defn.heapModifies.itervalues()])

		if reads != modifies:
			return False

		# It's sound to bypass the load.
		src = defn.localReads[defn.op.value]
		dst = g.localModifies[0]

		dst.canonical().redirect(src)
		g.localModifies = []

		return True

	return False


def collectLoads(dataflow):
	loads = set()

	def collect(node):
		if isinstance(node, graph.GenericOp) and node.isLoad():
			loads.add(node)

	dfs(dataflow, collect)

	return loads


def evaluateDataflow(dataflow):
	pg = predicate.buildPredicateGraph(dataflow)

	loads = collectLoads(dataflow)

	print "LOADS", len(loads)

	eliminated = 0

	# HACK keep evaluating each load until no further transforms are possible.
	changed = True
	while changed:
		changed = False
		for load in loads:
			if attemptTransform(load, pg):
				eliminated += 1
				changed = True

	print "ELIMINATED", eliminated
