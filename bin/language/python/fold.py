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

import ast
from util.python import apply


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
			value = apply.applyBinaryOp(op, l.object.pyobj, r.object.pyobj)
			obj = extractor.getObject(value)
			return ast.Existing(obj)
		except apply.ApplyError:
			pass
	return bop

def foldUnaryPrefixOpAST(extractor, uop):
	op = uop.op
	expr = uop.expr

	if existingConstant(expr):
		try:
			value = apply.applyUnaryPrefixOp(op, expr.object.pyobj)
			obj = extractor.getObject(value)
			return ast.Existing(obj)
		except apply.ApplyError:
			pass
	return uop

def foldBoolAST(extractor, op):
	expr = op.expr

	if existingConstant(expr):
		try:
			value = apply.applyBool(expr.object.pyobj)
			obj = extractor.getObject(value)
			return ast.Existing(obj)
		except apply.ApplyError:
			pass
	return op

def foldNotAST(extractor, op):
	expr = op.expr

	if existingConstant(expr):
		try:
			value = apply.applyNot(expr.object.pyobj)
			obj = extractor.getObject(value)
			return ast.Existing(obj)
		except apply.ApplyError:
			pass
	return op

def foldCallAST(extractor, node, func, args=(), kargs={}):
	assert not kargs, kargs

	for arg in args:
		if not existingConstant(arg):
			return node
	try:
		args = [arg.object.pyobj for arg in args]
		value = apply.applyFunction(func, args)
		obj = extractor.getObject(value)
		return ast.Existing(obj)
	except apply.ApplyError:
		pass

	return node

def foldIsAST(extractor, node):
	left  = node.left
	right = node.right
	if left is right:
		# Must alias
		obj = extractor.getObject(True)
		return ast.Existing(obj)
	elif isinstance(left, ast.Existing) and isinstance(node.right, ast.Existing):
		# Known objects
		obj = extractor.getObject(left.object is right.object)
		return ast.Existing(obj)

	return node
