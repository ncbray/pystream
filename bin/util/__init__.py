import sys
import types

def replaceGlobals(f, g):
	# HACK closure is lost
	assert isinstance(f, types.FunctionType), type(f)
	return types.FunctionType(f.func_code, g, f.func_name, f.func_defaults)

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

# Note that the unique name may change between runs, as it takes the id of a type.
def uniqueSlotName(descriptor):
	# HACK GetSetDescriptors are not really slots?
	assert isinstance(descriptor, (types.MemberDescriptorType, types.GetSetDescriptorType)), (descriptor, type(descriptor), dir(descriptor))
	name     = descriptor.__name__
	objClass = descriptor.__objclass__
	return "%s#%s#%d" % (name, objClass.__name__, id(objClass))


