__all__ = ['CallPath', 'Memoizer', 'explodeCombonations',
	   'assureDirectoryExists']

import os.path
import sys


import math


import types

def replaceGlobals(f, g):
	# HACK closure is lost
	assert isinstance(f, types.FunctionType), type(f)
	return types.FunctionType(f.func_code, g, f.func_name, f.func_defaults)

def numbits(size):
	if size <= 1:
		return 0
	else:
		return int(math.ceil(math.log(size, 2)))

def assureDirectoryExists(dirname):
	if not os.path.exists(dirname): os.makedirs(dirname)

def moduleForGlobalDict(glbls):
	assert '__file__' in glbls, "Global dictionary does not come from a module?"
	
	for name, module in sys.modules.iteritems():
		if module and module.__dict__ is glbls:
			assert module.__file__ == glbls['__file__']
			return (name, module)
	assert False

class CallPath(object):
	__slots__ = 'site', 'previous', 'children', 'recurse'
	def __init__(self, site, previous=None):
		self.site = site
		self.previous = previous
		self.children = {}
		self.recurse = False

	def findSite(self, site):
		current = self

		while current:
			if site == current.site:
				current.recurse = True
				return current
			current = current.previous
		return None

	def extend(self, site):
		# If the site exists in the path, back up
		# else, move forward.
		return self.findSite(site) or self.__getChild(site)

	def __getChild(self, site):
		if not site in self.children:
			self.children[site] = CallPath(site, self)
		return self.children[site]


	def __collect(self, l):
		if self.previous: self.previous.__collect(l)
		l.append(str(self.site))

	def __repr__(self):
		l = []
		self.__collect(l)
		return "path(%s)" % ', '.join(l)
		

class Memoizer(object):
	__slots__ = 'cache', 'callback'
	def __init__(self, callback):
		self.callback = callback
		self.cache = {}

	def __call__(self, *args):
		if not args in self.cache:
			self.cache[args] = self.callback(*args)
		return self.cache[args]

	def getStored(self, *args):
		if not args in self.cache:
			print
			print "GET STORED ERROR"
			print "WANTED"
			for arg in args:
				print '\t', arg
			print
			print "GOT"
			for k in self.cache.iterkeys():
				for arg in k:
					print '\t', arg
				print
##				print k == args
##				for a, b in zip(k, args):
##					print a == b, id(a), id(b)
			print
		
		assert args in self.cache, args
		return self.cache[args]


def __explodeCombonations(callback, limit, args, current, index):
	if index >= len(args):
		callback(*current)
	else:
		if limit and len(args[index]) > limit:
			# Don't explode a parameter that has a
			# multiplicity greater than "limit"
			current[index] = tuple(args[index])
			__explodeCombonations(callback, limit, args, current, index+1)			
		else:
			# For parameters with low multiplicity,
			# generate all possible combinations.
			for arg in args[index]:
				current[index] = arg
				__explodeCombonations(callback, limit, args, current, index+1)


def explodeCombonations(callback, limit, *args):
	current = [None for i in range(len(args))]
	index = 0
	__explodeCombonations(callback, limit, args, current, index)


# Assumes that the same arguments will create the same object,
# and different arguments will create different objects.
class Canonical(object):
	def __init__(self, create):
		self.create = create
		self.cache = {}

	def __call__(self, *args):
		if args not in self.cache:
			obj = self.create(*args)
			self.cache[args] = obj
			return obj
		else:
			return self.cache[args]

	def get(self, *args):
		return self(*args)

	def exists(self, *args):
		return args in self.cache
