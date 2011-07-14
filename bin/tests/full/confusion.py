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

from vec3 import vec3

def confuse(b):
	if b:
		return 1
	else:
		return 0

def beConfused(b):
	return confuse(b)


def passThrough(o):
	return o

def extractValue(v):
	return v.dot(v)

def confusedSite(b):
	if b:
		return vec3(7.0, 7.0, 7.0)
	else:
		return vec3(11.0, 11.0, 11.0)

def beConfusedSite(b):
	v = passThrough(confusedSite(b))
	return passThrough(extractValue(v))


def confuseConst(i):
	if i:
		return i
	else:
		return 1

def beConfusedConst(i):
	return confuseConst(i)

def confuseMethods(a, b, c, d, e, f):
	va = vec3(a, b, c)
	vb = vec3(d, e, f)

	if a > b:
		vc = va.cross(vb)
	else:
		vc = vb.cross(va)

	return vc.dot(vc)
