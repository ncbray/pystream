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

from opcode import *
from dis import findlinestarts

flowControlOps = [opmap['RETURN_VALUE'],
		  opmap['RAISE_VARARGS'],
		  opmap['FOR_ITER'],
		  opmap['BREAK_LOOP']]

flowControlOps.extend(hasjrel)
flowControlOps.extend(hasjabs)
#flowControlOps.remove(opmap['SETUP_LOOP'])

flowControlOps = frozenset(flowControlOps)

blockOps = frozenset((opmap['POP_BLOCK'], opmap['SETUP_LOOP'], opmap['SETUP_EXCEPT'], opmap['SETUP_FINALLY'], opmap['END_FINALLY']))


stackOps = frozenset((opmap['POP_TOP'], opmap['ROT_TWO'], opmap['ROT_THREE'], opmap['DUP_TOP'], opmap['ROT_FOUR'], opmap['DUP_TOPX']))



notOp = []
notOp.extend(stackOps)
notOp.extend(blockOps)
notOp.append(opmap['NOP'])
notOp = frozenset(notOp)

class Instruction(object):
	__slots__ = 'line', 'offset', 'opcode', 'arg'

	def __init__(self, line, offset, opcode, arg=None):
		self.line 	= line
		self.offset 	= offset
		self.opcode 	= opcode
		self.arg 	= arg

		assert self.hasArgument() or arg == None

	def __repr__(self):
		return "inst(%d:%d, %s, %s)" % (self.line, self.offset, self.neumonic(), repr(self.arg))

	def opcodeString(self):
		if self.hasArgument():
			return "%s %s" % (self.neumonic(), repr(self.arg))
		else:
			return self.neumonic()

	def neumonic(self):
		return opname[self.opcode]

	def hasArgument(self):
		return self.opcode >= HAVE_ARGUMENT

	def isFlowControl(self):
		return self.opcode in flowControlOps

	def isBlockOperation(self):
		return self.opcode in blockOps

	def isOperation(self):
		return self.opcode not in notOp

	def __eq__(self, other):
		return type(self) == type(other) and self.opcode == other.opcode and self.arg == other.arg

def disassemble(co):
	linestarts = dict(findlinestarts(co))

	code = co.co_code
	n = len(code)
	i = 0
	extended_arg = 0
	free = None

	line = 0

	inst = []

	offsetLUT = {}
	fixup = []

	while i < n:
		if i in linestarts:
			line = linestarts[i]

		c = code[i]
		op = ord(c)
		offset = i
		i = i+1

		if op >= HAVE_ARGUMENT:
			needsFixup = False
			oparg = ord(code[i]) + ord(code[i+1])*256 + extended_arg
			extended_arg = 0
			i = i+2

			if op == EXTENDED_ARG:
				assert False, "Cannot handle extended arguments: never encountered before."
				extended_arg = oparg*65536L

			if op in hasconst:
				arg = co.co_consts[oparg]
			elif op in hasname:
				arg = co.co_names[oparg]
			elif op in hasjrel:
				arg = i + oparg
				needsFixup = True
			elif op in hasjabs:
				arg = oparg
				needsFixup = True
			elif op in haslocal:
				arg = co.co_varnames[oparg]
			elif op in hascompare:
				arg = cmp_op[oparg]
			elif op in hasfree:
				if free is None: free = co.co_cellvars + co.co_freevars
				arg = free[oparg]
			else:
				arg = oparg

			newi = Instruction(line, offset, op, arg)
			if needsFixup: fixup.append(newi)

		else:
			newi = Instruction(line, offset, op)

		offsetLUT[offset] = len(inst)

		inst.append(newi)

	targets = []
	for fix in fixup:
		fix.arg = offsetLUT[fix.arg]
		targets.append(fix.arg)

	return inst, targets
