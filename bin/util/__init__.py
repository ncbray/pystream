__all__ = ['assureDirectoryExists', 'numbits', 'replaceGlobals']

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

def itergroupings(iterable, key, value):
	grouping = {}
	for i in iterable:
		group = key(i)
		data  = value(i)
		if not group in grouping:
			grouping[group] = [data]
		else:
			grouping[group].append(data)
	return grouping.iteritems()
