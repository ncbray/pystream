from . import base

class SetUnionSchema(base.Schema):
	__slots = ()
	def validate(self, arg):
		if arg is not None and not isinstance(arg, set):
			raise base.SchemaError, "Expected set, got %s" % type(arg).__name__
		else:
			return True

	def missing(self):
		return None

	def merge(self, *args):
		target, changed = self.inplaceMerge(None, *args)
		return target

	def inplaceMerge(self, target, *args):
		oldLen = len(target) if target else 0
		for arg in args:
			if arg:
				if target:
					target.update(arg)
				else:
					target = set(arg)
					
		newLen = len(target) if target else 0
		return target, oldLen != newLen

setUnionSchema = SetUnionSchema()

class SetIntersectionSchema(base.Schema):
	__slots = ()
	def validate(self, arg):
		if arg is not None and not isinstance(arg, set):
			raise base.SchemaError, "Expected set, got %s" % type(arg).__name__
		else:
			return True

	def missing(self):
		return None

	def merge(self, first, *args):
		if not first: return None
		
		target = set(first)

		for arg in args:
			if arg:
				target.intersection_update(arg)
				if not target: return None
			else:
				return None
					
		return target
	
	def inplaceMerge(self, target, *args):
		if not target: return None, False
		
		oldLen = len(target) if target else 0

		for arg in args:
			if arg:
				target.intersection_update(arg)
				if not target: return None, True
			else:
				return None, True
					
		newLen = len(target) if target else 0
		return target, oldLen != newLen

setIntersectionSchema = SetIntersectionSchema()
