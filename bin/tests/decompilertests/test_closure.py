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

from __future__ import absolute_import

from . decompiler_common import TestDecompiler, Dummy

class TestClosure1Decompile(TestDecompiler):
	s = """
def closure1():
	a = 0
	def g():
		return a
	return g(), g.func_name
"""


class TestClosure2Decompile(TestDecompiler):
	s = """
def closure2(i):
	a = i
	a += 1

	def g():
		return a
	return g(), g.func_name
"""
	inputs = [[-5], [3]]


class TestInlineFunc(TestDecompiler):
	s = """
def inlinefunc(a, b):
	def ilf(a, b):
		return a-b
	return ilf(a, b)*ilf(b,a), ilf.func_name
"""
	inputs = [[7, 3], [-10, 4]]
