from . import base

def union(*args):
	result, changed = inplaceUnion(None, *args)
	return result

def inplaceUnion(target, *args):
	oldLen = len(target) if target else 0
	for arg in args:
		if arg:
			if target:
				target.update(arg)
			else:
				target = set(arg)
				
	newLen = len(target) if target else 0
	return target, oldLen != newLen

def intersection(first, *args):
	if not first: return None
	
	target = set(first)

	for arg in args:
		if arg:
			target.intersection_update(arg)
			if not target: return None
		else:
			return None
				
	return target

def inplaceIntersection(target, *args):
	if not target: return None, False
	
	oldLen = len(target)

	for arg in args:
		if arg:
			target.intersection_update(arg)
			if not target: return None, True
		else:
			return None, True
				
	newLen = len(target) if target else 0
	return target, oldLen != newLen


class SetSchema(base.Schema):
	__slots = ()
	def validate(self, arg):
		if arg is not None and not isinstance(arg, set):
			raise base.SchemaError, "Expected set, got %s" % type(arg).__name__
		else:
			return True

	def missing(self):
		return None

	def copy(self, original):
		if original:
			return set(original)
		else:
			return None


class SetUnionSchema(SetSchema):
	__slots = ()

	def merge(self, *args):
		return union(*args)

	def inplaceMerge(self, *args):
		return inplaceUnion(*args)

setUnionSchema = SetUnionSchema()

class SetIntersectionSchema(SetSchema):
	__slots = ()

	def merge(self, *args):
		return intersection(*args)
	
	def inplaceMerge(self, *args):
		return inplaceIntersection(*args)

setIntersectionSchema = SetIntersectionSchema()
