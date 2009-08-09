import copy
from asttools.transform import *

# HACK should not be dependant on Python?
from language.python import ast

class InternalError(Exception):
	pass

class ApplyToCode(TypeDispatcher):
	def __init__(self, strategy):
		self.strategy = strategy

	@defaultdispatch
	def visitCode(self, node):
		assert node.isCode(), type(node)
		for child in node.children():
			self.strategy(child)
		return node

class MutateCode(TypeDispatcher):
	def __init__(self, strategy):
		self.strategy = strategy

	@defaultdispatch
	def visitCode(self, node):
		assert node.isCode(), type(node)
		replaceAllChildren(self.strategy, node)
		return node

class MutateCodeReversed(TypeDispatcher):
	def __init__(self, strategy):
		self.strategy = strategy

	@defaultdispatch
	def visitCode(self, node):
		assert node.isCode(), type(node)
		replaceAllChildrenReversed(self.strategy, node)
		return node

class DynamicBase(object):
	__slots__ = 'lut', 'shared'

	def __init__(self, d=None):
		if d is None:
			self.lut = {}
			self.shared = False
		else:
			self.lut = d
			self.shared = True

	def split(self):
		self.shared = True
		return DynamicDict(self.lut)

	def premutate(self):
		if self.shared:
			self.lut = copy.copy(self.lut)
			self.shared = False



class Undefined(object):
	def __str__(self):
		return "<lattice bottom>"

undefined = Undefined()


class Top(object):
	def __str__(self):
		return "<lattice top>"

top = Top()

class DynamicDict(DynamicBase):
	__slots__ = ()

	def lookup(self, key, default=undefined):
		if key in self.lut:
			return self.lut[key]
		else:
			return default

	def define(self, key, value):
		self.premutate()
		self.lut[key] = value

	def undefine(self, key):
		if key in self.lut:
			self.premutate()
			del self.lut[key]

def printlut(lut):
	print len(lut)

	keys = sorted(lut.iterkeys())

	for k in keys:
		print '\t', k, lut[k]

	print


def meet(meetF, *dynamic):
	debug = 0

	dynamic = [d for d in dynamic if d is not None]

	if not dynamic:
		return None, False
	elif len(dynamic) == 1:
		return dynamic[0], False
	else:
		if debug:
			print "Meet"
			for d in dynamic:
				printlut(d.lut)
			print

		out = DynamicDict()
		changed = False

		# Find all the keys
		keys = set(dynamic[0].lut.iterkeys())
		for other in dynamic[1:]:
			keys.update(other.lut.iterkeys())

		# Only merge if the values are identical
		for key in keys:
			values = []

			for other in dynamic:
				additional = other.lookup(key)
				if additional is top:
					merged = top
					break
				elif additional is not undefined:
					values.append(additional)
			else:
				if values:
					merged = meetF(values)
				else:
					merged = undefined

			if merged is not undefined:
				out.define(key, merged)

			if merged != dynamic[0].lookup(key):
				changed = True


		if debug:
			print "Out"
			printlut(out.lut)
			print

		# Changed indicates the first dnamic frame has been modified.
		return out, changed


class FlowDict(object):
	def __init__(self):
		self._current = DynamicDict()
		self.bags  = {}
		self.tryLevel = 0

	def save(self, name):
		if self._current is not None:
			if not name in self.bags: self.bags[name] = []
			self.bags[name].append(self._current)
			self._current = None

	# For reverse dataflow
	def restoreDup(self, name):
		assert name in self.bags, name
		assert len(self.bags[name]) == 1, self.bags[name]
		self._current = self.bags[name][0].split()


	def pop(self):
		old = self._current
		self._current = None
		return old

	def popSplit(self, count=2):
		assert count >= 2

		old = self._current
		self._current = None

		if old is not None:
			return [old] + [old.split() for i in range(count-1)]
		else:
			return [None for i in range(count)]

	def restore(self, dynamic):
		assert self._current is None
		self._current = dynamic

	def extend(self, name, bag):
		if not name in self.bags:
			self.bags[name] = []
		self.bags[name].extend(bag)

	def saveBags(self):
		old = self.bags
		self.bags = {}
		return old

	def restoreBags(self, bags):
		self.bags = bags

	def restoreAndMergeBags(self, originalbags, newbags):
		self.restoreBags(originalbags)
		for name, bag in newbags.iteritems():
			self.extend(name, bag)

	def mergeCurrent(self, meetF, name):
		assert self._current is None

		if name in self.bags:
			bag = self.bags[name]
			del self.bags[name]
		else:
			bag = []

		self._current, changed = meet(meetF, *bag)


	def define(self, key, value):
##		if self.tryLevel > 0:
##			print "Try", key, value
		if self._current is None:
			raise InternalError, "No flow contour exists."

		return self._current.define(key, value)

	def lookup(self, key):
		if self._current is None:
			raise InternalError, "No flow contour exists."
		return self._current.lookup(key)

	def undefine(self, key):
##		if self.tryLevel > 0:
##			print "Try", key, undefined

		if self._current is None:
			raise InternalError, "No flow contour exists."

		return self._current.undefine(key)



class MayRaise(TypeDispatcher):
	@defaultdispatch
	def default(self, node):
		return True

	@dispatch(list, tuple)
	def visitContainer(self, node):
		for child in node:
			if self(child):
				return True
		return False

	@dispatch(ast.Existing)
	def visitExisting(self, node):
		return False

	@dispatch(ast.Local)
	def visitLocal(self, node):
		return False

	@dispatch(ast.BuildTuple, ast.BuildList, ast.BuildMap)
	def visitBuild(self, node):
		return False

	@dispatch(ast.Delete)
	def visitDelete(self, node):
		return False # HACK assumes no undefined variables.


	@dispatch(ast.Assign)
	def visitAssign(self, node):
		return self(node.expr)

	@dispatch(ast.Discard)
	def visitDiscard(self, node):
		return self(node.expr)


	@dispatch(ast.Continue, ast.Break)
	def visitLoopFlow(self, node):
		return False

	@dispatch(ast.Return)
	def visitReturn(self, node):
		return self(node.exprs)
