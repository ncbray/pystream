from __future__ import absolute_import

import types
import inspect
from opcode import opmap
from language.python.ast import *
import common.ssa as ssa

from common import opnames

from . import pythonstack

from .. import errors


from language.python.fold import foldBinaryOpAST, foldUnaryPrefixOpAST, foldCallAST

import operator


from language.python.annotations import Origin

from language.python.simplecodegen import SimpleCodeGen
import sys

import re
isIdentifier = re.compile(r'^([a-zA-Z_]\w*)?$')

def splitBytes(value):
	return value>>8, value&0xFF

def isConstantOfType(node, t):
	return isinstance(node, Existing) and node.object.isConstant() and isinstance(node.object.pyobj, t)

def getConstant(node):
	return node.object.pyobj

# Does flow-insensitive constant folding.
# This will hopefully make later analysis slightly more efficient.
class InstructionTranslator(object):
	def __init__(self, code, moduleName, ssa, lcls, extractor, callback, trace=False):
		self.code = code
		self.moduleName = moduleName
		self.ssa = ssa
		self.initOpHandler()

		self.locals = lcls

		self.emitStoreLocal = True

		self.extractor = extractor
		self.callback = callback
		self.trace = trace

	def initOpHandler(self):
		self.ophandler = {}

		mungedopmap = {}
		for neumonic, number in opmap.iteritems():
			mungedopmap[neumonic.replace('+', '_')] = number

		for name in dir(self):
			if len(name) > 3 and name[:3] == 'op_':
				member = getattr(self, name)
				if isinstance(member, self.__init__.__class__):
					neumonic = name[3:]
					self.ophandler[mungedopmap[neumonic]] = member

	def writeLocal(self, name, value):
		if hasattr(value, 'name') and not value.name and isIdentifier.match(name):
			value.name = name

		if self.emitStoreLocal:
			lcl = self.readLocal(name)

			if lcl != value:
				self.emit(Assign(value, [lcl]))

	def readLocal(self, name):
		if not name in self.locals:
			self.locals[name] = Local(name)
		return self.locals[name]

	@property
	def stack(self):
		#return self.frame.stack
		return self._stack

	def discard(self):
		self.stack.discard()

	def peek(self):
		return self.stack.peek()

	def pop(self):
		return self.stack.pop()

	def pop2(self):
		two = self.pop()
		one = self.pop()
		return one, two

	def push(self, node):
		self.stack.push(node)

	# Stack management
	def op_DUP_TOP(self):
		self.stack.dup()

	def op_DUP_TOPX(self, count):
		self.stack.dupx(count)

	def op_POP_TOP(self):
		self.stack.discard()

	def op_ROT_THREE(self):
		self.stack.rot3()

	def op_ROT_TWO(self):
		self.stack.rot2()


	# Load
	def op_LOAD_FAST(self, name):
		self.push(self.readLocal(name))

	def op_DELETE_FAST(self, name):
		self.emit(Delete(self.readLocal(name)))


	# Creates an opaque iterator on the stack.
	def op_GET_ITER(self):
		self.pushOp(GetIter(self.getArg()))
		#self.push(pythonstack.Iter(self.getArg()))


	def makeConstant(self, value):
		return Existing(self.extractor.getObject(value))

	def pushConstant(self, value):
		#self.pushOp(self.makeConstant(value))
		self.push(self.makeConstant(value))

	def op_LOAD_CONST(self, value):
		self.pushConstant(value)

	def op_LOAD_GLOBAL(self, name):
		# HACK assumes that globals "True" and "False" and "None" evaluate to a constant.

		if name == "True":
			self.pushConstant(True)
		elif name == "False":
			self.pushConstant(False)
		elif name == "None":
			self.pushConstant(None)
		else:
			# Global must be treated like an op, as it can mutate.
			self.pushOp(GetGlobal(self.makeConstant(name)))

	def op_LOAD_NAME(self, name):
		# HACK in all cases encountered, LOAD_NAME seems to load a global.
		self.op_LOAD_GLOBAL(name)

	def op_STORE_NAME(self, name):
		# HACK in all cases encountered, STORE_NAME seems to load a global.
		self.op_STORE_GLOBAL(name)

	def op_STORE_GLOBAL(self, name):
		arg = self.getArg()

		if isinstance(arg, pythonstack.Definition):
			# Writing a "definition" into a global, redirect into a local.
			assert not arg in self.defn
			lcl = Local()
			self.defn[arg] = lcl
			arg = lcl

		self.emit(SetGlobal(self.makeConstant(name), arg))

	def op_DELETE_GLOBAL(self, name):
		self.emit(DeleteGlobal(self.makeConstant(name)))


	# Store
	def op_STORE_FAST(self, name):
		arg = self.getArg()

		if isinstance(arg, pythonstack.Definition):
			# Writing a "definition" into a local, capture the local instead.
			assert not arg in self.defn
			self.defn[arg] = self.readLocal(name)
		elif isinstance(arg, pythonstack.Iter):
			# Can occur inside list comprehensions.
			self.defn[pythonstack.loopIndex] = self.readLocal(name)
		else:
			self.writeLocal(name, arg)


	def op_STORE_ATTR(self, name):
		target = self.getArg()
		expr = self.getArg()

		if isinstance(expr, pythonstack.Definition):
			# Writing a "definition" into an attribute, redirect into a local.
			assert not expr in self.defn
			lcl = Local()
			self.defn[expr] = lcl
			expr = lcl

		self.emit(SetAttr(expr, target, self.makeConstant(name)))

	def op_DELETE_ATTR(self, name):
		target = self.getArg()
		self.emit(DeleteAttr(target, self.makeConstant(name)))

	# Subscripts
	def op_BINARY_SUBSCR(self):
		subscript = self.getArg()
		expr = self.getArg()

		self.pushOp(GetSubscript(expr, subscript))

	def op_STORE_SUBSCR(self):
		subscript = self.getArg()
		expr = self.getArg()
		value = self.getArg()


		if isinstance(value, pythonstack.Definition):
			# Writing a "definition" into a local, capture the local instead.
			assert not value in self.defn
			lcl = Local()
			self.defn[value] = lcl
			value = lcl

		self.emit(SetSubscript(value, expr, subscript))

	def op_DELETE_SUBSCR(self):
		subscript = self.getArg()
		expr = self.getArg()
		self.emit(DeleteSubscript(expr, subscript))


	# Binary Ops
	def op_BINARY_ADD(self):
		self.emitBinaryOp('+')

	def op_BINARY_SUBTRACT(self):
		self.emitBinaryOp('-')

	def op_BINARY_MULTIPLY(self):
		self.emitBinaryOp('*')

	def op_BINARY_FLOOR_DIVIDE(self):
		self.emitBinaryOp('//')

	def op_BINARY_DIVIDE(self):
		self.emitBinaryOp('/')

	def op_BINARY_TRUE_DIVIDE(self):
		self.emitBinaryOp('/')

	def op_BINARY_MODULO(self):
		self.emitBinaryOp('%')

	def op_BINARY_POWER(self):
		self.emitBinaryOp('**')

	def op_BINARY_LSHIFT(self):
		self.emitBinaryOp('<<')

	def op_BINARY_RSHIFT(self):
		self.emitBinaryOp('>>')

	def op_BINARY_AND(self):
		self.emitBinaryOp('&')

	def op_BINARY_OR(self):
		self.emitBinaryOp('|')

	def op_BINARY_XOR(self):
		self.emitBinaryOp('^')

	def op_COMPARE_OP(self, op):
		self.emitBinaryOp(op)


	# Inplace operations.

	def op_INPLACE_ADD(self):
		self.emitBinaryOp('+=')

	def op_INPLACE_SUBTRACT(self):
		self.emitBinaryOp('-=')

	def op_INPLACE_MULTIPLY(self):
		self.emitBinaryOp('*=')

	def op_INPLACE_FLOOR_DIVIDE(self):
		self.emitBinaryOp('//=')

	def op_INPLACE_DIVIDE(self):
		self.emitBinaryOp('/=')

	def op_INPLACE_TRUE_DIVIDE(self):
		self.emitBinaryOp('/=')

	def op_INPLACE_MODULO(self):
		self.emitBinaryOp('%=')

	def op_INPLACE_POWER(self):
		self.emitBinaryOp('**=')

	def op_INPLACE_LSHIFT(self):
		self.emitBinaryOp('<<=')

	def op_INPLACE_RSHIFT(self):
		self.emitBinaryOp('>>=')

	def op_INPLACE_AND(self):
		self.emitBinaryOp('&=')

	def op_INPLACE_XOR(self):
		self.emitBinaryOp('^=')

	def op_INPLACE_OR(self):
		self.emitBinaryOp('|=')


	# Unary Ops.
	def op_UNARY_POSITIVE(self):
		self.emitUnaryPrefixOp('+')

	def op_UNARY_NEGATIVE(self):
		self.emitUnaryPrefixOp('-')

	def op_UNARY_INVERT(self):
		self.emitUnaryPrefixOp('~')

	def getKwds(self, count):
		kwds = []
		for i in range(count):
			value = self.getArg()
			name = self.getArg()
			namedef = self.ssa.definition(name)
			assert isConstantOfType(namedef, str), namedef
			kwds.insert(0, (getConstant(namedef), value))
		return kwds


	def op_CALL_FUNCTION(self, count):
		kwd, positional = splitBytes(count)

		kargs = None
		vargs = None
		kwds = self.getKwds(kwd)
		args = self.getArgs(positional)
		expr = self.getArg()

		self.pushOp(Call(expr, args, kwds, vargs, kargs))



	def op_CALL_FUNCTION_VAR(self, count):
		kwd, positional = splitBytes(count)

		kargs = None
		vargs = self.getArg()

		kwds = self.getKwds(kwd)
		args = self.getArgs(positional)
		expr = self.getArg()

		self.pushOp(Call(expr, args, kwds, vargs, kargs))

	def op_CALL_FUNCTION_KW(self, count):
		kwd, positional = splitBytes(count)

		kargs = self.getArg()
		vargs = None

		kwds = self.getKwds(kwd)
		args = self.getArgs(positional)
		expr = self.getArg()

		self.pushOp(Call(expr, args, kwds, vargs, kargs))


	def op_CALL_FUNCTION_VAR_KW(self, count):
		kwd, positional = splitBytes(count)

		kargs = self.getArg()
		vargs = self.getArg()

		kwds = self.getKwds(kwd)
		args = self.getArgs(positional)
		expr = self.getArg()

		self.pushOp(Call(expr, args, kwds, vargs, kargs))

	def op_MAKE_FUNCTION(self, count):
		code = self.getArg()
		defn = self.ssa.definition(code)

		assert isConstantOfType(defn, types.CodeType), defn

		args = self.getArgs(count)

		func = self.callback(self.extractor, getConstant(defn), self.moduleName, self.trace)

		code = func

		self.pushOp(MakeFunction(args, (), code))

	def op_MAKE_CLOSURE(self, count):
		code = self.getArg()
		defn = self.ssa.definition(code)

		assert isConstantOfType(defn, types.CodeType), defn

		code = getConstant(defn)

		args = self.getArgs(count)


		numfree = len(code.co_freevars)
		assert numfree > 0


		closure = self.getArg()
		cdefn = self.ssa.definition(closure)
		assert isinstance(cdefn, BuildTuple), cdefn
		cells = cdefn.args


		# Make sure the names match.
		for cell, name in zip(cells, code.co_freevars):
			assert cell.name == name, (cell.name, name)

		# TODO check cell names are correct?

		func = self.callback(self.extractor, getConstant(defn), self.moduleName)

		code = func

		self.pushOp(MakeFunction(args, cells, code))



	# Structure manipulation

	def op_BUILD_LIST(self, count):
		self.pushOp(Allocate(Existing(self.extractor.getObject(list))))
		#self.pushOp(BuildList(self.getArgs(count)))

	def op_BUILD_MAP(self, count):
		# TODO count is a size hint... we should preserve it?
		self.pushOp(Allocate(Existing(self.extractor.getObject(dict))))
		#self.pushOp(BuildMap())

	def op_STORE_MAP(self):
		# HACK reduce STORE_MAP into a subscript
		key   = self.getArg()
		value = self.getArg()
		expr  = self.peek() # Dictionary not popped

		self.emit(SetSubscript(value, expr, key))

	def op_BUILD_SLICE(self, count):
		assert count == 2 or count == 3

		if count == 3:
			step = self.getArg()
		else:
			step = None

		stop = self.getArg()
		start = self.getArg()

		self.pushOp(BuildSlice(start, stop, step))


	def op_BUILD_TUPLE(self, count):
		self.pushOp(BuildTuple(self.getArgs(count)))

	def op_UNPACK_SEQUENCE(self, count):
		expr = self.getArg()

		if isinstance(expr, pythonstack.Definition):
			# Writing a "definition" into a tuple unpack.
			lcl = Local()
			self.defn[expr] = lcl
			expr = lcl


		defn = self.ssa.definition(expr)
		if isinstance(defn, BuildTuple):
			# Don't bother unpacking a tuple we just built.
			toStack = defn.args
		else:
			toStack = tuple([self.newLocal() for i in range(count)])
			unpack = UnpackSequence(expr, toStack)
			for lcl in toStack:
				self.ssa.define(lcl, unpack) # HACK?
			self.emit(unpack)

		# Push the targets on the stack in reverse order.
		r = range(len(toStack))
		r.reverse()
		for i in r:
			target = toStack[i]
			self.push(target)


	def op_LOAD_ATTR(self, name):
		target = self.getArg()
		self.pushOp(GetAttr(target, self.makeConstant(name)))

	# HACK reduce LIST_APPEND bytecodes into GetAttr and Call opcodes.
	def op_LIST_APPEND(self):
		arg = self.getArg()
		target = self.getArg()

		self.pushOp(GetAttr(target, self.makeConstant('append')))

		expr = self.getArg()

		self.emit(Discard(Call(expr, (arg,), (), None, None)))

	def op_SLICE_0(self):
		expr = self.getArg()
		self.pushOp(GetSlice(expr, None, None, None))

	def op_SLICE_1(self):
		a = self.getArg()
		expr = self.getArg()
		self.pushOp(GetSlice(expr, a, None, None))


	def op_SLICE_2(self):
		b = self.getArg()
		expr = self.getArg()
		self.pushOp(GetSlice(expr, None, b, None))

	def op_SLICE_3(self):
		b = self.getArg()
		a = self.getArg()
		expr = self.getArg()
		self.pushOp(GetSlice(expr, a, b, None))


	def op_STORE_SLICE_0(self):
		expr = self.getArg()
		value = self.getArg()
		self.emit(SetSlice(value, expr, None, None, None))

	def op_STORE_SLICE_1(self):
		a = self.getArg()
		expr = self.getArg()
		value = self.getArg()
		self.emit(SetSlice(value, expr, a, None, None))


	def op_STORE_SLICE_2(self):
		b = self.getArg()
		expr = self.getArg()
		value = self.getArg()
		self.emit(SetSlice(value, expr, None, b, None))

	def op_STORE_SLICE_3(self):
		b = self.getArg()
		a = self.getArg()
		expr = self.getArg()
		value = self.getArg()
		self.emit(SetSlice(value, expr, a, b, None))



	def op_DELETE_SLICE_0(self):
		expr = self.getArg()
		self.emit(DeleteSlice(expr, None, None, None))

	def op_DELETE_SLICE_1(self):
		a = self.getArg()
		expr = self.getArg()
		self.emit(DeleteSlice(expr, a, None, None))


	def op_DELETE_SLICE_2(self):
		b = self.getArg()
		expr = self.getArg()
		self.emit(DeleteSlice(expr, None, b, None))

	def op_DELETE_SLICE_3(self):
		b = self.getArg()
		a = self.getArg()
		expr = self.getArg()
		self.emit(DeleteSlice(expr, a, b, None))


	def op_SETUP_LOOP(self, jmp):
		pass # HACK, should use the information?

	def op_POP_BLOCK(self):
		pass # HACK, should use the information?

	def readCell(self, name):
		assert isinstance(name, str)
		return Cell(name)


	def op_LOAD_CLOSURE(self, i):
		self.push(self.readCell(i))
		#self.pushOp(GetCell(self.readCell(i)))

	def op_LOAD_DEREF(self, i):
		self.pushOp(GetCellDeref(self.readCell(i)))

	def op_STORE_DEREF(self, i):
		arg = self.getArg()
		cell = self.readCell(i)
		if isinstance(arg, pythonstack.Definition):
			# Writing a "definition" into a local, capture the local instead.
			assert not arg in self.defn
			self.defn[arg] = cell

		else:
			self.emit(SetCellDeref(arg, cell))


	def op_UNARY_NOT(self):
		expr = self.getArg()
		uop = Not(expr)
		uop = foldCallAST(self.extractor, uop, operator.not_, (expr,))
		self.pushOp(uop)

	def op_YIELD_VALUE(self):
		self.pushOp(Yield(self.getArg()))

	def op_PRINT_ITEM_TO(self):
		f = self.getArg()
		value = self.getArg()
		self.emit(Print(f, value))

	def op_PRINT_NEWLINE_TO(self):
		f = self.getArg()
		value = None
		self.emit(Print(f, value))

	def op_PRINT_ITEM(self):
		f = None
		value = self.getArg()
		self.emit(Print(f, value))

	def op_PRINT_NEWLINE(self):
		f = None
		value = None
		self.emit(Print(f, value))



	def op_IMPORT_NAME(self, name):
		fromlist = self.ssa.definition(self.getArg())

		# TODO could use strong assert, but how do we know if a tuple is constant?
		assert isinstance(fromlist, Existing), fromlist
		#assert isConstantOfType(fromlist, (tuple, type(None))), fromlist
		fromlist = getConstant(fromlist)

		rel = self.ssa.definition(self.getArg())
		assert isConstantOfType(rel, int), rel
		rel = getConstant(rel)

		self.pushOp(Import(name, fromlist, rel))

	def op_IMPORT_FROM(self, name):
		module = self.peek()

		# HACK convert import from into a GetAttr
		self.pushOp(GetAttr(module, self.makeConstant(name)))

	# Utility functions
	def getArgs(self, count):
		args = []
		for i in range(count):
			args.insert(0, self.getArg())
		return args

	def getArg(self):
		arg = self.pop()
		return arg

	def emitUnaryPrefixOp(self, op):
		expr = self.getArg()
		uop = UnaryPrefixOp(op, expr)
		uop = foldUnaryPrefixOpAST(self.extractor, uop)
		self.pushOp(uop)

	def emitBinaryOp(self, op):
		right = self.getArg()
		left  = self.getArg()

		bop = BinaryOp(left, op, right)
		bop = foldBinaryOpAST(self.extractor, bop)

		if isinstance(bop, BinaryOp) and bop.op in opnames.inplaceOps:
			self.pushAssign(bop.left, bop)
		else:
			self.pushOp(bop)

	def newLocal(self):
		return Local()

	def setOpOrigin(self, op):
		if not isinstance(op, (Local, Existing)):
			op.rewriteAnnotation(origin=(Origin(self.code.co_name, self.code.co_filename, self.lineno),))
			assert op.annotation.origin

	def pushOp(self, op):
		res = self.ssa.define(self.newLocal(), op)
		self.pushAssign(res, op)

	def pushAssign(self, target, op):
		self.push(target)

		if target != op:
			self.emit(Assign(op, [target]))


	def emit(self, op):
		assert self.exit == None


		if isinstance(op, (Assign, Discard)):
			self.setOpOrigin(op.expr)
		else:
			self.setOpOrigin(op)


		ssa.emitInstruction(op, self.ops)

	def translate(self, instructions, stack):
		self._stack = stack
		self.ops = []
		self.defn = {}
		self.exit = None

		self.instructions = instructions # HACK

		# Disbatch each instruction and emulate the stack.
		for inst in instructions:
			self.lineno = inst.line
			handler = self.ophandler.get(inst.opcode)

			if not handler:
				raise errors.UnsupportedOpcodeError, (inst.neumonic()+' '+str(inst.arg))

			if inst.hasArgument():
				handler(inst.arg)
			else:
				handler()


		return self.ops, self.defn, self._stack
