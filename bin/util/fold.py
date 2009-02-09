import operator
from common import opnames

class FoldError(Exception):
	pass

def foldFunction(func, vargs=(), kargs={}):
	try:
		result = func(*vargs, **kargs)
	except:
		raise FoldError, "Error folding '%s'" % str(func)

	return result

def foldBinaryOp(op, l, r):
	if not op in opnames.binaryOpName:
		raise FoldError, "Unreconsized binary operator: %r" % op

	name = opnames.binaryOpName[op]
	func = getattr(operator, name)
	return foldFunction(func, (l, r))


def foldUnaryPrefixOp(op, expr):
	if not op in opnames.unaryPrefixOpName:
		raise FoldError, "Unreconsized unary prefix operator: %r" % op

	name = opnames.unaryPrefixOpName[op]
	func = getattr(operator, name)
	return foldFunction(func, (expr,))

def foldBool(expr):
	return foldFunction(bool, (expr,))

def foldNot(expr):
	return foldFunction(operator.not_, (expr,))
