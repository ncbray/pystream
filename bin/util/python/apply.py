import operator
from . import opnames

class ApplyError(Exception):
	pass

def applyFunction(func, vargs=(), kargs={}):
	try:
		result = func(*vargs, **kargs)
	except:
		raise ApplyError, "Error folding '%s'" % str(func)

	return result

def applyBinaryOp(op, l, r):
	if not op in opnames.binaryOpName:
		raise ApplyError, "Unreconsized binary operator: %r" % op

	name = opnames.binaryOpName[op]
	func = getattr(operator, name)
	return applyFunction(func, (l, r))


def applyUnaryPrefixOp(op, expr):
	if not op in opnames.unaryPrefixOpName:
		raise ApplyError, "Unreconsized unary prefix operator: %r" % op

	name = opnames.unaryPrefixOpName[op]
	func = getattr(operator, name)
	return applyFunction(func, (expr,))

def applyBool(expr):
	return applyFunction(bool, (expr,))

def applyNot(expr):
	return applyFunction(operator.not_, (expr,))
