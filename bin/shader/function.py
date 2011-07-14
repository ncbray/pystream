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

def clamp(x, minVal, maxVal):
	return min(max(x, minVal), maxVal)

def smoothstep(edge0, edge1, x):
	t = clamp((x-edge0)/(edge1-edge0), 0.0, 1.0)
	return t*t*(3-2*t)
