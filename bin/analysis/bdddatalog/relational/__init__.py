from __future__ import absolute_import

import pycudd
from . import util
from . managerhack import m
from . domain import LogicalDomain, PhysicalDomain, PhysicalStructure, makeEncoder


def validateAttributes(attributes):
	p = set()
	for name, pdomain in attributes.iteritems():
		assert isinstance(name, str)
		assert isinstance(pdomain, PhysicalDomain)
		if pdomain in p:
			return False
		else:
			p.add(pdomain)
	return True


class Relation(object):
	__slots__ = 'data', 'attributes', 'encoder'

	def __init__(self, attributes, data=None):
		assert isinstance(attributes, (tuple, list)), type(attributes)
		
		self.attributes = tuple(attributes)

		if data==None:
			data = m.ReadLogicZero()
			
		self.data = data

		self.encoder = makeEncoder(self)

	def buildEncoder(self, encoder):
		for name, domain in self.attributes:
			domain.buildEncoder(encoder)

	def entry(self, *args, **kargs):
		assert not args or kargs and args or not kargs

		if kargs and not args:
			e = util.restrictMask(m, self.attributes, kargs)
		elif args and not kargs:
			e = util.restrictMaskOrdered(m, self.attributes, args)
		else:
			assert False

		return Relation(self.attributes, e)

	def bdd(self):
		return self.data

	def isFalse(self):
		return self.data == m.ReadLogicZero()

	def isTrue(self):
		return self.data == m.ReadOne()

	def maybeFalse(self):
		return not self.isTrue()
	
	def maybeTrue(self):
		return not self.isFalse()

	def maybeEither(self):
		return self.maybeTrue() and self.maybeFalse()

	def __eq__(self, other):
		return type(other) == type(self) and self.attributes == other.attributes and self.data == other.data

	def __ne__(self, other):
		return type(other) != type(self) or self.attributes != other.attributes or self.data != other.data

	def __nonzero__(self):
		return bool(self.data)


	def __or__(self, other):
		return self.union(other)

	def __invert__(self):
		return self.invert()


	def invert(self):
		return Relation(self.attributes, ~self.data)

	def union(self, other):
		assert self.attributes == other.attributes
		return Relation(self.attributes, self.data | other.data)		

	def restrict(self, **kargs):
		rn = util.createRestrict(m, self.attributes, kargs)
		e = util.restrictMask(m, self.attributes, kargs)
		return Relation(rn, self.data.Restrict(e))

	def rename(self, **kargs):
		rn = util.createRename(m, self.attributes, kargs)
		return Relation(rn, self.data)
		
	def relocate(self, **kargs):
		rn, p = util.createRelocate(m, self.attributes, kargs)
		return Relation(rn, self.data.Permute(p))

	# Rename and relocate.
	def modify(self, **kargs):
		rn, p = util.createModify(m, self.attributes, kargs)
		return Relation(rn, self.data.Permute(p))

	def forget(self, *args):
		rn, cube = util.createForget(m, self.attributes, args)
		return Relation(rn, self.data.ExistAbstract(cube))
	
	def join(self, other):
		rn = util.createJoin(m, self.attributes, other.attributes)
		return Relation(rn, self.data&other.data)

	# Join and forget joined fields.
	def compose(self, other):
		rn, cube = util.createCompose(m, self.attributes, other.attributes)
		return Relation(rn, self.data.AndAbstract(other.data, cube))

	def enumerateList(self):
		data = []		
		def addData(*args):
			data.append(args)

		self.enumerate(addData)
		return data

	def enumerate(self, callback):
		Enumerator(self).enumerate(callback)
	
class Enumerator(object):
	def __init__(self, relation):
		self.relation = relation

		self.indexes = []
		self.bits = {}
		self.values = {}

		self.maximum = []


		#fields = [name for name, domain in relation.attributes]

		self.shape = self.__accumulateAttributes(relation.attributes)

		self.indexes.sort()
		#self.indexes.reverse()

	def __accumulateAttributes(self, attributes):
		shape = []
		for name, domain in attributes:

			if isinstance(domain, PhysicalDomain):
				pos = len(self.maximum)
	
				self.indexes.extend(domain.index)
				self.bits.update(domain.bitlut)
				
				for index, value in domain.bitvalue.iteritems():
					self.values[index] = (pos, value)

				self.maximum.append(domain.logical.range)
			else:
				assert isinstance(domain, PhysicalStructure)
				pos = self.__accumulateAttributes(domain.attributes)

			shape.append(pos)

		return tuple(shape)

	def enumerate(self, callback):
		inital = [0 for f in range(len(self.maximum))]		
		self.__enumerate(0, inital, self.relation.data, callback)

	def reshape(self, shape, current):
		if isinstance(shape, int):
			return current[shape]
		else:
			return tuple([self.reshape(s, current) for s in shape])

	def __enumerate(self, loc, current, data, callback):
		if not data:
			return # Early out.
		
		if loc >= len(self.indexes):
			callback(*self.reshape(self.shape, current))
		else:
			index = self.indexes[loc]
			bit = self.bits[index]
			pos, value = self.values[index]

			# Be sure to iterate the correct way, or this will be expensive.
##			# Sanity check
##			if data != one():
##				i = data.NodeReadIndex()
##				assert i >= index, (i, index) # TODO correct ordering?

			self.__enumerate(loc+1, current, data.Restrict(~bit), callback)
			current[pos] |= value

			# Do not enumerate values outside the domain's range.
			if current[pos] < self.maximum[pos]:
				self.__enumerate(loc+1, current, data.Restrict(bit), callback)
				
			current[pos] &= ~value

def one():
	return m.ReadOne()

def zero():
	return m.ReadLogicZero()
