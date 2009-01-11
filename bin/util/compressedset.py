def union(*args):
	result, changed = inplaceUnion(nullSet, *args)
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
	if not first: return nullSet
	target = set(first)

	for arg in args:
		if arg:
			target.intersection_update(arg)
			if not target: return nullSet
		else:
			return nullSet
	return target

def inplaceIntersection(target, *args):
	if not target: return nullSet, False
	
	oldLen = len(target)

	for arg in args:
		if arg:
			target.intersection_update(arg)
			if not target: return nullSet, True
		else:
			return nullSet, True
				
	newLen = len(target) if target else 0
	return target, oldLen != newLen


def copy(target):
	if target:
		return set(target)
	else:
		return nullSet

def validate(target):
	return target is nullSet or isinstance(target, set)

nullSet = None
