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

def loadPairs(fn):
	f = open(fn)

	count = 0
	edges = []

	for line in f:
		# Pairs start at "1", so shift.
		edge =  tuple([int(node)-1 for node in line.split()])
		edges.append(edge)
		count = max(count, *edge)

	f.close()

	return count+1, edges
