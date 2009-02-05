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

def elapsedTimeString(t):
	if t < 1.0:
		return "%.1f ms" % (t*1000.0)
	elif t < 60.0:
		return "%.2f s" % (t)
	elif t < 3600.0:
		return "%.2f m" % (t/60.0)
	else:
		return "%.2f h" % (t/3600.0)

def memorySizeString(sz):
	sz = float(sz)
	if sz < 1024:
		return "%f B" % sz
	elif sz < 1024**2:
		return "%.1f kB" % (sz/(1024))
	elif sz < 1024**3:
		return "%.1f MB" % (sz/(1024**2))
	else:
		return "%.1f GB" % (sz/(1024**3))

# Note that the unique name may change between runs, as it takes the id of a type.
def uniqueSlotName(descriptor):
	# HACK GetSetDescriptors are not really slots?
	assert isinstance(descriptor, (types.MemberDescriptorType, types.GetSetDescriptorType)), (descriptor, type(descriptor), dir(descriptor))
	name     = descriptor.__name__
	objClass = descriptor.__objclass__
	return "%s#%s#%d" % (name, objClass.__name__, id(objClass))
