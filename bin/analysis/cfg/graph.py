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

class NoNormalFlow(Exception):
	pass


class CFGBlock(object):
	__slots__ = 'region', 'next', 'data'
	exitNames = ()

	def __init__(self, region):
		self.region = region
		self.next = {}

	def validExitName(self, name):
		return name in self.exitNames

	def setExit(self, name, other):
		assert self.validExitName(name)
		assert name not in self.next

		if other is not None:
			self.next[name] = other
			other.addPrev(self, name)

	def getExit(self, name):
		assert self.validExitName(name)
		return self.next.get(name)

	def killExit(self, name):
		if name in self.next:
			self.next[name].removePrev(self, name)
			del self.next[name]

	def addPrev(self, other, name):
		raise NotImplementedError

	def removePrev(self, other):
		raise NotImplementedError

	def replacePrev(self, other):
		raise NotImplementedError

	def forward(self):
		return self.next.itervalues()

	def normalForward(self):
		result = []
		for name, next in self.next.iteritems():
			if name not in ('error', 'fail', 'yield'):
				result.append(next)
		return result

	def findExit(self, e):
		name = None
		for k, v in self.next.iteritems():
			if v is e:
				name = k
				break
		return name

	def redirectExit(self, oldExit, newExit):
		name = self.findExit(oldExit)
		assert name is not None

		self.killExit(name)
		self.setExit(name, newExit)

	def forwardExit(self, other, name):
		assert other is not None

		if name in other.next:
			next = other.next[name]
			del other.next[name]
		else:
			next = None

		selfExit = self.findExit(other)
		assert selfExit is not None
		self.killExit(selfExit)

		if next:
			self.next[selfExit] = next
			next.replacePrev(other, name, self, selfExit)

	def stealExit(self, other, name):
		assert other is not None
		self.setExit(name, other.popExit(name))

	def popExit(self, name):
		e = self.next.get(name)
		if e is not None:
			del self.next[name]
			e.removePrev(self, name)
		return e


	def sanityCheck(self):
		# TODO check MIMO cases?
		for child in self.forward():
			assert self in child.reverse(), self

		for child, name in self.iterprev():
			assert child.getExit(name) is self, self

	def destroy(self):
		for k, v in self.next.iteritems():
			v.removePrev(self, k)
		self.next = {}

	def transferExit(self, dstName, other, srcName):
		e = other.next[srcName]
		del other.next[srcName]

		assert dstName not in self.next

		self.next[dstName] = e
		e.replacePrev(other, srcName, self, dstName)

	def clonedExit(self, name, dst):
		self.next[name] = dst

	def insertAtExit(self, exitName, block, blockExitName):
		#self{exitName} -> current
		# to
		#self{exitName} -> block{blockExitName} -> current

		current = self.next[exitName]
		current.replacePrev(self, exitName, block, blockExitName)

		self.next[exitName] = block
		block.addPrev(self, exitName)
		block.next[blockExitName] = current


class SingleEntryBlock(CFGBlock):
	__slots__ = '_prev',

	def __init__(self, region):
		CFGBlock.__init__(self, region)
		self._prev = (None, '')

	def addPrev(self, other, name):
		assert isinstance(other, CFGBlock)
		assert self._prev[0] is None, self
		self._prev = (other, name)

	def removePrev(self, other, name):
		assert isinstance(other, CFGBlock)
		assert self._prev == (other, name)
		self._prev = (None, '')

	def replacePrev(self, other, otherName, replacement, replacementName):
		assert isinstance(other, CFGBlock)
		assert isinstance(replacement, CFGBlock)
		assert self._prev == (other, otherName)
		self._prev = (replacement, replacementName)

	def clonedPrev(self, prev, name):
		self._prev = (prev, name)

	def reverse(self):
		return (self._prev[0],)

	def iterprev(self):
		return (self._prev,)

	def redirectEntries(self, other):
		if self._prev[0] is not None:
			self.prev.redirectExit(self, other)

	@property
	def prev(self):
		return self._prev[0]

class MultiEntryBlock(CFGBlock):
	__slots__ = '_prev',

	def __init__(self, region):
		CFGBlock.__init__(self, region)
		self._prev = []

	def clonedPrev(self, prev, name):
		assert isinstance(prev, CFGBlock)
		self._prev.append((prev, name))

	def addPrev(self, other, name):
		assert isinstance(other, CFGBlock)
		self._prev.append((other, name))

	def removePrev(self, other, name):
		index = self._prev.index((other, name))
		del self._prev[index]

	def replacePrev(self, other, otherName, replacement, replacementName):
		key = (other, otherName)
		if not key in self._prev:
			print key
			print self._prev
			print

		index = self._prev.index(key)
		self._prev[index] = (replacement, replacementName)

	def reverse(self):
		return [p[0] for p in self._prev]

	def redirectEntries(self, other):
		old, self._prev = self._prev, []

		for prev, prevName in old:
			prev.redirectExit(self, other)

	def numPrev(self):
		return len(self._prev)

	def iterprev(self):
		return self._prev


class Entry(CFGBlock):
	__slots__ = ()
	exitNames = ('entry')

	def reverse(self):
		return ()

	def iterprev(self):
		return ()


class Exit(SingleEntryBlock):
	__slots__ = ()
	exitNames = ()

class Suite(SingleEntryBlock):
	__slots__ = 'ops'
	exitNames = ('normal', 'fail', 'error')

	def __init__(self, region):
		SingleEntryBlock.__init__(self, region)
		self.ops = []

	def simplify(self):
		if len(self.ops) == 0:
			if self.prev:
				old = self.prev
				old.forwardExit(self, 'normal')
				self.destroy()
				return old
			else:
				self.destroy()
		else:
			return self


class Switch(SingleEntryBlock):
	__slots__ = 'condition'

	exitNames = ('true', 'false', 'fail', 'error')

	def __init__(self, region, condition):
		SingleEntryBlock.__init__(self, region)
		self.condition = condition

class TypeSwitch(SingleEntryBlock):
	__slots__ = 'original'

	exitNames = ('fail', 'error')

	def __init__(self, region, original):
		SingleEntryBlock.__init__(self, region)
		self.original = original

	def validExitName(self, name):
		return name in self.exitNames or (isinstance(name, int) and name >= 0 and name < len(self.original.cases))



class State(SingleEntryBlock):
	__slots__ = 'name'

	exitNames = ('normal')

	def __init__(self, region, name):
		SingleEntryBlock.__init__(self, region)
		self.name = name


class Merge(MultiEntryBlock):
	__slots__ = ('phi')
	exitNames = ('normal')

	def __init__(self, region):
		MultiEntryBlock.__init__(self, region)
		self.phi = []

	def simplify(self):
		if len(self._prev) == 1 and not self.phi:
				self._prev[0][0].forwardExit(self, 'normal')


	def addPrev(self, other, name):
		assert isinstance(other, CFGBlock)
		assert not self.phi
		MultiEntryBlock.addPrev(self, other, name)

	def removePrev(self, other, name):
		assert isinstance(other, CFGBlock)

		index = self._prev.index((other, name))
		del self._prev[index]

		self.phi = [phi.dropArgument(index) for phi in self.phi]

	def redirectEntries(self, other):
		assert isinstance(other, CFGBlock)
		assert not self.phi

		old, self.prev = self.prev, []

		for prev in old:
			prev.redirectExit(self, other)

class Yield(SingleEntryBlock):
	__slots__ = ()
	exitNames = ('normal')

class Code(object):
	__slots__ = ['code', 'returnParam',
				 'entryTerminal', 'normalTerminal',
				 'failTerminal', 'errorTerminal']

	def __init__(self):
		self.entryTerminal  = Entry(None)
		self.normalTerminal = Exit(None)
		self.failTerminal   = Exit(None)
		self.errorTerminal  = Exit(None)
