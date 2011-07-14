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

import unittest


import os
import os.path

def isTestFileName(fn):
	return len(fn) >= 9 and fn[:5] == "test_" and fn[-3:] == '.py'

def moduleName(base, root, fn):
	fullPath = os.path.join(root, fn)
	path, ext = os.path.splitext(fullPath)
	path = removePrefix(base, path)
	path = path.replace(os.path.sep, ".")
	return path

def removePrefix(base, path):
	assert path[:len(base)] == base
	return path[len(base)+len(os.path.sep):]

def wantFile(filename, only, exclude):
	old = filename

	base, ext = os.path.splitext(old)

	while old != base:
		if base in only:
			return True

		if base in exclude:
			return False

		old = base
		base, part = os.path.split(old)

	return not only

def findTests(base, only, exclude):
	names = []

	for root, dirs, files in os.walk(base):
		for fn in files:
			if isTestFileName(fn) and wantFile(os.path.join(root, fn), only, exclude):
				name = moduleName(base, root, fn)
				names.append(name)
	return names


def getModule(name):
	parts  = name.split('.')
	module = __import__(name)

	for part in parts[1:]:
		module = getattr(module, part)

	return module

# NOTE unlike the builtin version, this does NOT catch import errors.  This helps debugging.
# TODO turn import errors into test errors?
def loadTestsFromNames(self, names):
	suites = [self.loadTestsFromModule(getModule(name)) for name in names]
	return self.suiteClass(suites)


def runTests(path, only=set(), exclude=set()):
	# If no tests are specified, find them.
	if not os.path.isdir(path):
		raise TypeError, '"%s" is not a directory.' % path

	testList = findTests(path, only, exclude)

	print "/========== Tests ==========\\"
	for test in testList:
		print "| %s" % test
	print "\\===========================/"
	print

	suite = loadTestsFromNames(unittest.defaultTestLoader, testList)

	#unittest.TextTestRunner(verbosity=2).run(suite)
	unittest.TextTestRunner().run(suite)
