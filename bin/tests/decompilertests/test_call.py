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

from . decompiler_common import TestDecompiler

##class TestDiscardDecompile(TestDecompiler):
##	s = """
##def f(o, v, f):
##	f(o, v)
##	return o.x
##"""
##	inputs = [[Dummy(), 1, dummySet], [Dummy(), 1.0, dummySet], [Dummy(), True, dummySet], [Dummy(), 'foo', dummySet]]
##


def gatherArgs(*args, **kargs):
	return args, kargs


class TestFuncVargsDecompile(TestDecompiler):
	s = """
def fvargs(*args):
	return args
"""
	inputs = [[3, 2, 4, 7]]


class TestFuncKargsDecompile(TestDecompiler):
	s = """
def fkargs(kargs):
	def fkargsinner(**kargs):
		return kargs
	return fkargsinner(**kargs)
"""
	inputs = [[{'a':1, 'b':2, 'c':3}]]


class TestCallStdDecompile(TestDecompiler):
	s = """
def callstd(f):
	return f(1, 2, 3)
"""
	inputs = [[gatherArgs]]



class TestCallKwdDecompile(TestDecompiler):
	s = """
def callkwd(f):
	return f(1, 2, 3, foo='bar', thing='thang')
"""
	inputs = [[gatherArgs]]


class TestCallVargsDecompile(TestDecompiler):
	s = """
def callvargs(f):
	args = (1, 2, 3)
	return f(0, foo='bar', thing='thang', *args)
"""
	inputs = [[gatherArgs]]

class TestCallKargsDecompile(TestDecompiler):
	s = """
def callkargs(f):
	kargs = {'foo':'bar', 'thing':'thang'}
	return f(0, 1, help='me', **kargs)
"""
	inputs = [[gatherArgs]]


class TestCallVargsKargsDecompile(TestDecompiler):
	s = """
def callkargs(f, a, b):
	kargs = {'foo':'bar', 'thing':'thang'}
	return f(0, 1, help=a+b, *(1, 2, 3), **kargs)
"""
	inputs = [[gatherArgs, 'm', 'e']]
