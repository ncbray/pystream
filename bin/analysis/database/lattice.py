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
	return isinstance(arg, set)

def setUnionCreate():
	return set()

def setUnionMerge(argiter):
	out = set()
	for arg in argiter:
		out.update(arg)
	return out

def inplaceSetUnionMerge(target, argiter):
	for arg in argiter:
		target.update(arg)
	return target

setUnionSchema = LatticeSchema(setUnionValidate, setUnionCreate,
			       setUnionMerge, inplaceSetUnionMerge)
