# Copyright 2011 Nicholas Bray
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
