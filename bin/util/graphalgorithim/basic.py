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

def reverseDirectedGraph(G):
	out = {}
	for node, nexts in G.iteritems():
		for next in nexts:
			if next not in out:
				out[next] = [node]
			else:
				out[next].append(node)
	return out

def findEntryPoints(G):
	entryPoints = set(G.iterkeys())
	for nexts in G.itervalues():
		for next in nexts:
			if next in entryPoints:
				entryPoints.remove(next)
	return list(entryPoints)
