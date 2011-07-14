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

import collections

def colorGraph(G):
	# Assumes G[node] -> iterable(nodes), a in G[b] implies b in G[a]

	solution   = {}
	numColors  = 0
	constraint = collections.defaultdict(set)
	group      = []


	pending   = set()
	remaining = {}

	for node, values in G.iteritems():
		remaining[node] = len(values)
		pending.add(node)

	while pending:
		# Select the next node to color
		# HACK search for node with max remaining neighbors.
		maxRemain = -1
		maxNode   = None
		for node in pending:
			if remaining[node] > maxRemain:
				maxNode   = node
				maxRemain = remaining[node]
		assert maxNode is not None
		pending.remove(maxNode)

		# Determine the color of the node
		current = maxNode
		for color in range(numColors):
			if color not in constraint[current]:
				break
		else:
			color = numColors
			numColors += 1
			group.append([])

		solution[current] = color
		group[color].append(current)
		for other in G[current]:
			remaining[other] -= 1
			constraint[other].add(color)

	return solution, group, numColors
