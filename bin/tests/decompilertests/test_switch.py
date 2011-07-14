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


class TestMultiSwitchDeompile(TestDecompiler):
	s = """
def multiswitch(a, b):
	w = 0
	if a:
		s = 9
		x = 1
		if b:
			y = 2*x
		else:
			y = 3*x
		z = 4
	else:
		x = 5
		if b:
			y = 6*x
		else:
			y = 7*x
		z = 8
		s = 10
	return w, x, y, z, s
"""
	inputs = [[False, False], [True, False], [False, True], [True, True]]



class TestConstantSwitchDeompile(TestDecompiler):
	s = """
def f():
	if True:
		return 1
	else:
		return 0
"""
	inputs = [[]]

class TestConstantCompoundSwitch1Deompile(TestDecompiler):
	s = """
def cc1(s):
	if True and s:
		return 1
	else:
		return 0
"""
	inputs = [[False], [True]]


class TestConstantCompoundSwitch2Deompile(TestDecompiler):
	s = """
def cc2(s):
	if s and True:
		return 1
	else:
		return 0
"""
	inputs = [[False], [True]]


class TestConstantCompoundSwitch3Deompile(TestDecompiler):
	s = """
def cc3(s):
	if False and s:
		return 1
	else:
		return 0
"""
	inputs = [[False], [True]]


class TestConstantCompoundSwitch4Deompile(TestDecompiler):
	s = """
def cc4(s):
	if s and False:
		return 1
	else:
		return 0
"""
	inputs = [[False], [True]]



class TestConstantCompoundSwitch5Deompile(TestDecompiler):
	s = """
def cc5(s):
	if True or s:
		return 1
	else:
		return 0
"""
	inputs = [[False], [True]]


class TestConstantCompoundSwitch6Deompile(TestDecompiler):
	s = """
def cc6(s):
	if s or True:
		return 1
	else:
		return 0
"""
	inputs = [[False], [True]]


class TestConstantCompoundSwitch7Deompile(TestDecompiler):
	s = """
def cc7(s):
	if False or s:
		return 1
	else:
		return 0
"""
	inputs = [[False], [True]]


class TestConstantCompoundSwitch8Deompile(TestDecompiler):
	s = """
def cc8(s):
	if s or False:
		return 1
	else:
		return 0
"""
	inputs = [[False], [True]]


class TestSwitch1Deompile(TestDecompiler):
	s = """
def f(a):
	if a > 0:
		return True
	else:
		return False
	return 'blah'
"""
	inputs = [[0], [1], [-1], [2]]



class TestSwitch2Deompile(TestDecompiler):
	s = """
def f(a):
	if a > 0:
		res = True
	else:
		res = False
	return res
"""
	inputs = [[0], [1], [-1], [2]]

class TestSwitch3Deompile(TestDecompiler):
	s = """
def f(a):
	if a > 0:
		return True
	else:
		res = False
	return res
"""
	inputs = [[0], [1], [-1], [2]]


class TestSwitch4Deompile(TestDecompiler):
	s = """
def f(a):
	if a > 0:
		res = True
	else:
		return False
	return res
"""
	inputs = [[0], [1], [-1], [2]]
