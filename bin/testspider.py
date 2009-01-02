from __future__ import absolute_import

import unittest


import os
import os.path

def isTestFileName(fn):
	return len(fn) >= 9 and fn[:5] == "test_" and fn[-3:] == '.py'

def testModuleName(base, root, fn):
	fullPath = os.path.join(root, fn)
	path, ext = os.path.splitext(fullPath)
	path = removePrefix(base, path)
	path = path.replace(os.path.sep, ".")
	return path
	
##	parts = path.split(os.path.sep)
##	assert parts[0] == "."
##	return ".".join(parts[1:])

def removePrefix(base, path):
	assert path[:len(base)] == base
	return path[len(base)+len(os.path.sep):]

def findTests(base):
	names = []
	for root, dirs, files in os.walk(base):
		for fn in files:
			if isTestFileName(fn):
				name = testModuleName(base, root, fn)
				names.append(name)
	return names


def runTests(path, testList=None, exclude=set()):
	# If no tests are specified, find them.
	if not os.path.isdir(path):
		raise TypeError, '"%s" is not a directory.' % path
	
	if testList is None: testList = findTests(path)

	# Filter out explicitly excluded tests.
	exclude = frozenset(exclude)
	testListSet = frozenset(testList)


	header = False
	for s in exclude:
		if s not in testListSet:
			if not header:
				print "WARNING: attempted to exclude the following non-existant tests..."
				header = True
			print '\t%s' % s
	if header:
		print
	
	testList = [s for s in testList if s not in exclude]

	print "/========== Tests ==========\\"
	for test in testList:
		print "| %s" % test
	print "\\===========================/"
	print
	
		
	suite = unittest.defaultTestLoader.loadTestsFromNames(testList)
	
	#unittest.TextTestRunner(verbosity=2).run(suite)
	unittest.TextTestRunner().run(suite)
