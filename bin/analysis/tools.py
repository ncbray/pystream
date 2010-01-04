from . astcollector import getOps

def codeOps(code):
	ops, lcls = getOps(code)
	return ops

def codeLocals(code):
	ops, lcls = getOps(code)
	return lcls

def codeOpsLocals(code):
	return getOps(code)

def mightHaveSideEffect(op):
	modifies = op.annotation.modifies
	if modifies and not modifies[0]:
		return False
	return True

def singleObject(lcl):
	references = lcl.annotation.references
	if references:
		refs = references[0]
		if len(refs) == 1:
			obj = refs[0].xtype.obj
			if obj.isPreexisting():
				return obj
	return None

def singleCall(op):
	invokes = op.annotation.invokes

	if invokes and invokes[0]:
		targets = set([code for code, context in invokes[0]])
		if len(targets) == 1:
			return targets.pop()

	return None


emptySet = frozenset()

def opInvokesContexts(code, op, opContext):
	invokes = op.annotation.invokes

	if invokes:
		cindex = code.annotation.contexts.index(opContext)
		if invokes[1][cindex]:
			return frozenset([context for func, context in invokes[1][cindex]])

	return emptySet
