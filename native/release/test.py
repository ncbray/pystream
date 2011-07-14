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

import time
import pybind

a = pybind.vec3(1.0, 2.0, 3.0)
b = pybind.vec3(2.0, 1.0, 3.0)

def dot(a, b):
	return a.x*b.x+a.y*b.y+a.z*b.z


def dummy(a, b):
	pass

def test(f):
	start = time.clock()
	for i in range(1000000):
		f(a, b)
	return time.clock()-start



t1 = test(pybind.dot)
t2 = test(dummy)

print t1/t2
