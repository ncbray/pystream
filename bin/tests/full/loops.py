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

# TODO starting constant?
def whileLoop(start):
	a = start
	while a < 1.0:
		a = a+0.3
	return a



class LL(object):
	__slots__ = 'next'
	def __init__(self, next=None):
		self.next = next

	# HACK, inheritance should automatically find this.
	def __bool__(self):
		return True

class Pair(object):
	__slots__ = 'a', 'b'
	def __init__(self, a, b):
		self.a = a
		self.b = b

def buildList(size):
	head = None
	while size > 0:
		head = LL(head)
		size = size-1
	return head

def buildListBackwards(size):
	head = None
	current = None

	while size > 0:
		head = LL()
		if current:
			current.next = head
		current = head
		size = size-1
	return head


def buildListSwitch(size):
	a = None
	b = None

	while size > 0:
		a, b = LL(b), LL(a)
		size = size-1

	# TODO make tuple?
	return Pair(a, b)


### Can't handle asymetric returns? ###

##def isPrime(num):
##	if num%2==0: return False
##	test = 3
##	while test < num:
##		if num%test == 0:
##			return False
##		else:
##			test = test + 2
##	return True

def isPrime(num):
	if num == 2:	return True
	if num%2 == 0:	return False

	test = 3
	prime = True
	while test < num:
		if num%test == 0:
			prime = False
		test = test + 2
	return prime

### Requires datastore support ###

def findPrimesWhile(limit):
	primes = [2]
	current = 3
	while current < limit:
		if isPrime(current):
			primes.append(current)
		current = current + 2
	return primes
