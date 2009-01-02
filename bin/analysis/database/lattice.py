from . import base

class LatticeSchema(base.Schema):
	__slots__ = 'validateCallback', 'missing', 'merge', 'inplaceMerge'

	def __init__(self, validate, missing, merge, inplaceMerge=None):
		self.validateCallback = validate
		self.missing = missing
		self.merge = merge
		self.inplaceMerge = inplaceMerge if inplaceMerge is not None else merge
		

	def validate(self, args):
		if not self.validateCallback(args):
			raise base.SchemaError, "Argument is not the correct type of value."

def setUnionValidate(arg):
	if not isinstance(arg, set):
		raise base.SchemaError, "Expected set, got %s" % type(arg).__name__
	else:
		return True

def setUnionCreate():
	return set()

def setUnionMerge(*args):
	out = set()
	for arg in args:
		out.update(arg)
	return out

def inplaceSetUnionMerge(target, *args):
	for arg in args:
		target.update(arg)
	return target

##setUnionSchema = LatticeSchema(setUnionValidate, setUnionCreate,
##			       setUnionMerge, inplaceSetUnionMerge)


def setCompressedUnionValidate(arg):
	if arg is not None and not isinstance(arg, set):
		raise base.SchemaError, "Expected set, got %s" % type(arg).__name__
	else:
		return True

def setCompressedUnionCreate():
	return None

def setCompressedUnionMerge(*args):
	return inplaceSetCompressedUnionMerge(None, *args)

def inplaceSetCompressedUnionMerge(target, *args):
	for arg in args:
		if arg:
			if target:
				target.update(arg)
			else:
				target = set(arg)
	return target

setUnionSchema = LatticeSchema(setCompressedUnionValidate, setCompressedUnionCreate,
			       setCompressedUnionMerge, inplaceSetCompressedUnionMerge)
