import ast
from util import fold


def existingConstant(node):
	return isinstance(node, ast.Existing) and node.object.isConstant()


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
