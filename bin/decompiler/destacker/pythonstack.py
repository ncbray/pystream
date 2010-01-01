import copy
from language.python.ast import Local, Assign, Cell, Expression, Existing


class OpaqueStackElement(Expression):
	pass

class Iter(OpaqueStackElement):
	__slots__ = 'expr'
	def __init__(self, expr):
		self.expr = expr

class Definition(OpaqueStackElement):
	__slots__ = 'name'
	def __init__(self, name):
		self.name = name
	def isConstant(self):
		return False
	def __repr__(self):
		return "Definition(%s)" % repr(self.name)

loopIndex 		= Definition('loop index')
exceptionValue 		= Definition('exception value')
exceptionType 		= Definition('exception type')
exceptionTraceback 	= Definition('exception traceback')
flowInfo 		= Definition('flow information')

class DeferedMerge(OpaqueStackElement):
	__slots__ = 'target', 'elements', 'onExits'

	def __init__(self, elements, onExits):
		self.target = None
		self.elements = elements
		self.onExits = onExits

	def evaluate(self, target=None):
		# Prevent multiple evaluations
		if not self.target:

			# If the merges are chained, try to use the same target?
			if not target:
				self.target = Local(None)
			else:
				self.target = target

			# Create the partial merges
			for e, onExit in zip(self.elements, self.onExits):
				if isinstance(e, DeferedMerge):
					e = e.evaluate(self.target)

				if self.target != e:
					asgn = Assign(e, self.target)
					asgn.markMerge()
					onExit.append(asgn)

		return self.target

class PythonStack(object):
	def __init__(self):
		self.stack = []

	def size(self):
		return len(self.stack)

	def push(self, value):
		assert isinstance(value, (Local, Cell, OpaqueStackElement, Existing)), value
		self.stack.append(value)

	def peek(self):
		assert len(self.stack) >= 1
		top = self.stack[-1]
		if isinstance(top, DeferedMerge):
			top = top.evaluate()
		return top

	def pop(self):
		assert len(self.stack) >= 1
		top = self.stack.pop()
		if isinstance(top, DeferedMerge):
			top = top.evaluate()
		return top

	def discard(self):
		assert len(self.stack) >= 1
		self.stack.pop()

	def dup(self):
		assert len(self.stack) >= 1
		self.push(self.stack[-1])

	def dupx(self, count):
		assert len(self.stack) >= count
		self.stack.extend(self.stack[-count:])

	def rot2(self):
		assert len(self.stack) >= 2
		top = self.stack[-1]
		self.stack[-1] = self.stack[-2]
		self.stack[-2] = top

	def rot3(self):
		assert len(self.stack) >= 3
		top = self.stack[-1]
		self.stack[-1] = self.stack[-2]
		self.stack[-2] = self.stack[-3]
		self.stack[-3] = top

	# TODO badly named, similar to "dup"
	def duplicate(self):
		stack = PythonStack()
		stack.stack = copy.copy(self.stack)
		return stack

	def __iter__(self):
		return iter(self.stack)

	def __len__(self):
		return len(self.stack)

	def __eq__(self, other):
		if type(self) == type(other):
			return self.stack == other.stack
		else:
			return False

	def dump(self):
		for element in self.stack:
			print element

def same(l):
	if not l:
		return True

	for e in l:
		if e != l[0]:
			return False
	return True

def mergeStacks(stacks, onExits):
	out = PythonStack()

	assert len(stacks) > 0

	if len(stacks) == 1:
		return stacks[0]

	for stack in stacks:
		assert len(stack) == len(stacks[0]), (stack.stack, stacks[0].stack)

	for elements in zip(*[stack.stack for stack in stacks]):
		if not same(elements):
			# Just because the stacks are different does not mean we need to merge.
			# The different elements may be discarded in subsequent blocks.
			# Defered merges create the merge only if the stack element is used.
			element = DeferedMerge(elements, onExits)
		else:
			element = elements[0]
		out.push(element)

	return out
