import ast
from util import fold


def existingConstant(node):
	return isinstance(node, ast.Existing) and node.object.isConstant()

def foldSwitch(node):
	# Note: condtion.conditional may be killed, as
	# it is assumed to be a reference.

	# Constant value
	cond = node.condition.conditional
	if existingConstant(cond):
		value = cond.object.pyobj
		taken = node.t if value else node.f
		return ast.Suite([node.condition.preamble, taken])

	# Switch does nothing.
	if not node.t.blocks and not node.f.blocks:
		return node.condition.preamble

	return node


def foldBinaryOpAST(extractor, bop):
	l = bop.left
	op = bop.op
	r = bop.right

	if existingConstant(l) and existingConstant(r):
		try:
			value = fold.foldBinaryOp(op, l.object.pyobj, r.object.pyobj)
			obj = extractor.getObject(value)
			return ast.Existing(obj)
		except fold.FoldError:
			pass
	return bop

def foldUnaryPrefixOpAST(extractor, uop):
	op = uop.op
	expr = uop.expr

	if existingConstant(expr):
		try:
			value = fold.foldUnaryPrefixOp(op, expr.object.pyobj)
			obj = extractor.getObject(value)
			return ast.Existing(obj)
		except fold.FoldError:
			pass
	return uop

def foldBoolAST(extractor, op):
	expr = op.expr

	if existingConstant(expr):
		try:
			value = fold.foldBool(expr.object.pyobj)
			obj = extractor.getObject(value)
			return ast.Existing(obj)
		except fold.FoldError:
			pass
	return op

def foldNotAST(extractor, op):
	expr = op.expr

	if existingConstant(expr):
		try:
			value = fold.foldNot(expr.object.pyobj)
			obj = extractor.getObject(value)
			return ast.Existing(obj)
		except fold.FoldError:
			pass
	return op

def foldCallAST(extractor, node, func, args=(), kargs={}):
	assert not kargs, kargs

	for arg in args:
		if not existingConstant(arg):
			return node
	try:
		args = [arg.object.pyobj for arg in args]
		value = fold.foldFunction(func, args)
		obj = extractor.getObject(value)
		return ast.Existing(obj)
	except fold.FoldError:
		pass

	return node
