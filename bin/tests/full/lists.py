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

def pack(a, b, c):
	return [a, b, c]

def nothing(o):
	return o

def listTest(a, b, c):
	t = pack(a, b, c) # pack
	t = nothing(t) # list as argument, return value
	d, e, f = t # unpack
	return d+e-f


def constList():
	return [1, 2, 3]

def addConstList():
	a, b, c = constList()
	return a+b+c

def hybridList(x):
	return [1, 2, x]

def addHybridList(x):
	a, b, c = hybridList(x)
	return a+b+c

def makeConstCompound():
	return [[[1, 2], [3, 4]], [[5, 6], [7, 8]]]

def unpackConstCompound():
	((a, b), (c, d)), ((e, f), (g, h)) = makeConstCompound()
	return a*1+b*2+c*3+d*4+e*5+f*6+g*7+h*8

def makeCompound(a, b, c, d):
	return [[a, b, 1], [c, d, -1]]

def unpackCompound(a, b, c, d):
	(e, f, g), (h, i, j) = makeCompound(a, b, c, d)
	return e*1+f*2+g*3+h*4+i*5+j*6

def swap(a, b):
	f = [a, b]
	b, a = f
	return a, b

def index():
	return [1, 2, 3][1]
