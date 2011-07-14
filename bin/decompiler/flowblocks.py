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

import collections

class CFGEdge(object):
	def __init__(self, source, destination):
		assert not destination or destination.isPrevious(source)
		self.source = source
		self.destination = destination

	def redirect(self, newdest):
		newdest.setPrevious(self.source)
		self.source.replaceNext(self.destination, newdest)
		self.destination.replacePrev(self.source, None)

		olddest, self.destination = self.destination, newdest

		return olddest

	def __repr__(self):
		return "%s(%s, %s)" % (type(self).__name__, repr(self.source), repr(self.destination))


	def __eq__(self, other):
		if isinstance(other, type(self)):
			return self.source == other.source and self.destination == other.destination
		else:
			return False

	def __ne__(self, other):
		if isinstance(other, type(self)):
			return self.source != other.source or self.destination != other.destination
		else:
			return True


class FlowBlock(object):
	def __init__(self, region, origin):
		self.setRegion(region)
		self.origin = origin
		self.marked = False

	def setPrevious(self, prev):
		#assert self.prev == None
		assert prev.region == self.region
		self.prev = prev

	def replacePrev(self, current, new):
		assert self.prev == current, (self.prev, current)
		self.prev = new

	def entry(self):
		return self

	def exit(self):
		return self


	def isRegion(self):
		return False

	def numExits(self):
		return 1

	def numEntries(self):
		return 1

	def isSESE(self):
		return self.numEntries() == 1 and self.numExits() == 1

	def setRegion(self, region):
		assert not region or region.isRegion()
		assert self != region
		self.region = region

	def isPrevious(self, prev):
		return self.prev == prev

	def hasNormalExit(self):
		return True

	def mark(self):
		self.marked = True

class Linear(FlowBlock):
	def __init__(self, region, origin):
		FlowBlock.__init__(self, region, origin)

		self.instructions = []
		self.prev = None
		self.next = None

	def replaceNext(self, current, next):
		assert self.next == current
		self.next = next

	def setNext(self, next):
		self.next = next
		next.setPrevious(self)

	def getNext(self):
		return (self.next,)

	def __repr__(self):
		return "%s(%s)" % (type(self).__name__, repr(self.instructions))

	def containsOperations(self):
		for inst in self.instructions:
			if inst.isOperation():
				return True
		return False


class Merge(FlowBlock):
	def __init__(self, region):
		FlowBlock.__init__(self, region, None)

		# HACK A cludge to keep track of the incoming edges.
		self.incoming = set()
		self.incomingCount = collections.defaultdict(lambda: 0)
		self.totalCount = 0

		self.next = None

		self.loopMerge = False
		self.loopEntry = None

	def setLoopEntry(self, entry):
		assert not self.loopMerge
		self.loopMerge = True
		self.loopEntry = entry

	def setPrevious(self, prev):
		if prev:
			self.addIncoming(prev)

	def replacePrev(self, current, new):
		assert self.totalCount == self.__total()

		if current:
			assert current in self.incoming, (current, new, self.incoming)
			self.removeIncoming(current)

		if new:
			assert new.region == self.region
			self.addIncoming(new)

		assert self.totalCount == self.__total()


	def __total(self):
		total = 0
		for v in self.incomingCount.values():
			total += v
		return total

	def addIncoming(self, block):
		assert block.region == self.region
		assert self.incomingCount[block] < block.numExits()

		self.incoming.add(block)

		self.incomingCount[block] += 1
		self.totalCount += 1

	def removeIncoming(self, block):
		assert self.totalCount > 0
		assert block in self.incoming, (block, self.incoming)
		assert self.incomingCount[block] > 0

		self.incomingCount[block] -= 1
		self.totalCount -= 1

		if not self.incomingCount[block]:
			self.incoming.remove(block)
			del self.incomingCount[block]


	def replaceNext(self, current, next):
		assert self.next == current
		self.next = next

	def setNext(self, next):
		self.next = next
		next.setPrevious(self)

	def getNext(self):
		return (self.next,)

	def numEntries(self):
		return self.totalCount

	def isPrevious(self, prev):
		return prev in self.incoming

	def isShortCircutMerge(self):
		# If more that one switch leads into this merge,
		# the switches must be short circuts.
		count = 0
		for prev in self.incoming:
			if isinstance(prev, Switch):
				count += self.incomingCount[prev]
				if count > 1: return True
		return False

	def incomingSet(self):
		return set(self.incoming)

	def findLoopEntry(self, body):
		entry = self.loopEntry

		if not entry:
			entry = None
			for i in self.incoming:
				if i != body:
					assert not entry
					entry = i
			assert entry
		else:
			assert entry in self.incoming

		return entry


	def pulloutMerge(self, t, f):
		assert self.numEntries() >= 2

		assert t in self.incoming
		assert f in self.incoming

		if self.numEntries() > 2:
			m = Merge(self.region)

			self.replacePrev(t, None)
			t.replaceNext(self, m)
			m.setPrevious(t)

			self.replacePrev(f, None)
			f.replaceNext(self, m)
			m.setPrevious(f)

			m.setNext(self)

			assert m.isPrevious(t)
			assert m.isPrevious(f)
			assert self.isPrevious(m)
			assert not self.isPrevious(t)
			assert not self.isPrevious(f)

			assert m.numEntries() == 2
			assert self.incomingCount[m] == 1, self.incomingCount[m]

			return CFGEdge(m, self)
		else:
			assert self.numEntries() == 2
			assert self.isPrevious(t)
			assert self.isPrevious(f)
			assert self.next.isPrevious(self), self.next

			return CFGEdge(self, self.next)


	def pulloutMerge1(self, t):
		assert self.numEntries() >= 1

		assert False, "KILL"

		if self.numEntries() > 1:
			m = Merge(self.region)

			self.replacePrev(t, None)
			t.replaceNext(self, m)
			m.setPrevious(t)
			m.setNext(self)
			self.setPrevious(m)

			return CFGEdge(m, self)
		else:
			return CFGEdge(self, self.next)


	def eliminate(self):
		assert self.numEntries() == 1

		prev = tuple(self.incomingSet())[0]
		next = self.next

		prev.replaceNext(self, next)
		next.replacePrev(self, prev)

		self.replaceNext(next, None)
		self.replacePrev(prev, None)

class AbstractSwitch(FlowBlock):
	def __init__(self, region, origin):
		FlowBlock.__init__(self, region, origin)

		self.prev = None
		self.t = None
		self.f = None

		self.cond = CheckStack(region, origin)

	def replaceNext(self, current, next):
		if self.t == current:
			self.t = next
		elif self.f == current:
			self.f = next
		else:
			assert False

	def setNext(self, t, f):
		self.t = t
		t.setPrevious(self)

		self.f = f
		f.setPrevious(self)

	def getNext(self):
		return (self.t, self.f)

	def numExits(self):
		return 2

	def hasNormalExit(self):
		return False


class Switch(AbstractSwitch):
	def isShortCircut(self):
		f = lambda branch: branch and isinstance(branch, Merge) and branch.isShortCircutMerge()
		return f(self.t) or f(self.f)

class ForIter(FlowBlock):
	def __init__(self, region, origin):
		FlowBlock.__init__(self, region, origin)
		self.prev = None
		self.iter = None
		self.done = None

	def replaceNext(self, current, next):
		if self.iter == current:
			self.iter = next
		elif self.done == current:
			self.done = next
		else:
			assert False

	def setNext(self, iter, done):
		self.iter = iter
		iter.setPrevious(self)

		self.done = done
		done.setPrevious(self)

	def getNext(self):
		return (self.iter, self.done)

	def numExits(self):
		return 2

	def hasNormalExit(self):
		return False


class NormalEntry(FlowBlock):
	def __init__(self, region):
		FlowBlock.__init__(self, region, None)
		self.prev = None
		self.next = None

	def setPrevious(self, prev):
		assert False, prev

	def replaceNext(self, current, next):
		assert self.next == current
		self.next = next

	def setNext(self, next):
		self.next = next
		next.setPrevious(self)

	def getNext(self):
		return (self.next,)

	def numExits(self):
		return 1

	def numEntries(self):
		return 0

class NormalExit(FlowBlock):
	def __init__(self, region):
		FlowBlock.__init__(self, region, None)
		self.prev = None
		self.next = None

	def replaceNext(self, current, next):
		assert False

	def setNext(self, next):
		assert False

	def getNext(self):
		return ()

	def numExits(self):
		return 0


class ExceptionalFlowBlock(FlowBlock):
	def __init__(self, region, origin):
		FlowBlock.__init__(self, region, origin)
		self.prev = None


	def replaceNext(self, current, next):
		assert False

	def setNext(self):
		pass

	def getNext(self):
		return ()

	def numExits(self):
		return 0


class Return(ExceptionalFlowBlock):
	pass

class Break(ExceptionalFlowBlock):
	pass

class Continue(ExceptionalFlowBlock):
	pass

class Raise(ExceptionalFlowBlock):
	def __init__(self, region, origin, nargs):
		super(Raise, self).__init__(region, origin)
		assert nargs >= 0 and nargs <= 3
		self.nargs = nargs


class EndFinally(ExceptionalFlowBlock):
	def __init__(self, region, origin):
		ExceptionalFlowBlock.__init__(self, region, origin)

		self.prev = None
		self.next = None

	def replaceNext(self, current, next):
		assert self.next == current
		self.next = next

	def setNext(self, next):
		self.next = next
		next.setPrevious(self)

	def getNext(self):
		if self.next:
			return (self.next,)
		else:
			return ()

	def numExits(self):
		return 1 if self.next != None else 0




class FlowRegion(FlowBlock):
	def __init__(self, region, origin):
		FlowBlock.__init__(self, region, origin)

		self.prev = None
		self.normal = None
		self.exceptional = None

		self.next = None # HACK for switches.

		self._entry 	= NormalEntry(self)
		self._exit 	= NormalExit(self)

	def entry(self):
		return self._entry

	def exit(self):
		return self._exit

	def setHead(self, head):
		self.entry().setNext(head)

	def replaceNext(self, current, next):
		assert self.normal == current or self.exceptional == current, (current, self.normal, self.exceptional)

		if self.normal == current:
			self.normal = next
		elif self.exceptional == current:
			self.exceptional = next

	def setNext(self, normal, exceptional):
		assert not self.normal
		assert not self.exceptional

		self.normal = normal
		if normal: normal.setPrevious(self)

		self.exceptional = exceptional
		if exceptional: exceptional.setPrevious(self)

	def getNext(self):
		if not self.normal:
			if not self.exceptional:
				return ()
			else:
				return (self.exceptional,)
		else:
			if not self.exceptional:
				return (self.normal,)
			else:
				return (self.normal, self.exceptional)

	def isRegion(self):
		return True


	def numExits(self):
		return 2

class SESERegion(FlowRegion):
	def setNext(self, next):
		self.next = next
		if next: next.setPrevious(self)

	def numExits(self):
		return 1

	def replaceNext(self, current, next):
		assert self.next == current
		self.next = next

	def getNext(self):
		return (self.next,)

	def hasNormalExit(self):
		return self.next != None

class SwitchRegion(SESERegion):
	__slots__ = 'cond', 't', 'f'

	name = 'switch region'

	def __init__(self, region, origin, cond, t, f):
		super(SwitchRegion, self).__init__(region, origin)
		self.cond = cond
		self.t = t
		self.f = f

class AbstractShortCircut(object):
	def __init__(self, region, origin, *terms):
		self.region = region
		self.origin = origin

		self.terms = []

		assert len(terms) > 1

		if isinstance(terms[0], type(self)):
			self.terms.extend(terms[0].terms)
		else:
			self.terms.append(terms[0])

		for term in terms[1:]:
			assert isinstance(term, Linear) or term.complete()
			if isinstance(term, type(self)):
				self.terms.extend(term.terms)
			else:
				self.terms.append(term)

	def complete(self):
		if isinstance(self.terms[0], Linear):
			return True
		else:
			return self.terms[0].complete()

	def replaceDefault(self, newterm):
		inital = self.terms[0].replaceDefault(newterm)
		return type(self)(self.region, self.origin, inital, *self.terms[1:])

	def dump(self, tabs = ''):
		print tabs+type(self).__name__
		for term in self.terms:
			if isinstance(term, AbstractShortCircut):
				term.dump(tabs+'\t')
			else:
				print tabs+'\t'+repr(term)

	def __repr__(self):
		return "%s(%s)" % (type(self).__name__, ", ".join([repr(term) for term in self.terms]))

class CheckStack(object):
	def __init__(self, region, origin):
		self.region = region
		self.origin = origin

	def complete(self):
		return False

	def dump(self, tabs):
		print tabs+"Check Stack"

	def replaceDefault(self, newterm):
		return newterm

	def __repr__(self):
		return "CheckStack(%d)" % id(self)

class ShortCircutOr(AbstractShortCircut):
	pass

class ShortCircutAnd(AbstractShortCircut):
	pass

class LoopElse(SESERegion):
	name = 'loop else'

	@property
	def loop(self):
		return self.entry().next

	@property
	def _else(self):
		loop = self.loop
		if loop.normal and not isinstance(loop.normal, Merge):
			return loop.normal
		else:
			return None

class TryFinally(SESERegion):
	name = 'try finally'

	@property
	def tryBlock(self):
		return self.entry().next

	@property
	def finallyBlock(self):
		return self.tryBlock.exceptional.next

class TryExcept(SESERegion):
	name = 'try except'

class SuiteRegion(SESERegion):
	name = 'suite'

class CodeBlock(FlowRegion):
	name = 'function'

	def setNext(self, head):
		assert False
		self.entry().setNext(head)

	def numExits(self):
		return 0

	def replaceNext(self, current, next):
		assert False

	def getNext(self):
		return ()

class LoopRegion(FlowRegion):
	pass

class ExceptRegion(FlowRegion):
	pass

class FinallyRegion(FlowRegion):
	pass

class ForLoop(SESERegion):
	__slots__ = 'body'

	name = 'for loop'

	def __init__(self, region, origin, body):
		super(ForLoop, self).__init__(region, origin)
		self.body = body

class WhileLoop(SESERegion):
	__slots__ = 'cond', 'linearcond', 'body'
	name = 'while loop'

	def __init__(self, region, origin, cond, linearcond, body):
		super(WhileLoop, self).__init__(region, origin)
		self.cond = cond
		self.linearcond = linearcond
		self.body = body
