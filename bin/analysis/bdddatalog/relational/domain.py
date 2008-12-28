from __future__ import absolute_import

from . managerhack import m, intarray

import math

from util import numbits


class LogicalDomain(object):
	__slots__ = 'name', 'range', 'numbits', '__physical'
	
	def __init__(self, name, r):
		assert isinstance(name, str)
		self.name = name
		assert r >= 0
		self.range = r
		self.numbits = numbits(r)
		assert 2**self.numbits >= r, (self.numbits, r)
		self.__physical = []

	def physical(self, start, stride):
		p = PhysicalDomain(self, start, stride)
		self.__physical.append(p)
		return p

	def contains(self, value):
		return value >= 0 and value < self.range


class PhysicalDomain(object):
	__slots__ = 	['logical', 'bits', #'ibits',
			'bitlut', 'bitvalue',
			'cube', 'domain', 'index',
			 'tree', 'encodecache', 'encoder',]

	def __init__(self, l, start, stride):
		self.logical = l

		stop = start+stride*self.logical.numbits

		rl = len(range(start, stop, stride))
		assert  rl == self.logical.numbits, (rl, self.logical.numbits)

		# TODO Why the reverse?
		self.bits = [m.IthVar(i) for i in range(start, stop, stride)]
		self.bits.reverse()

		#self.ibits = [~bit for bit in self.bits]
		
		self.index = [b.NodeReadIndex() for b in self.bits]

		self.bitlut = {}
		self.bitvalue = {}
		for i in range(self.logical.numbits):
			self.bitvalue[self.index[i]] = 2**i
			self.bitlut[self.index[i]] = self.bits[i]

		#TODO More efficient way?
		self.domain = m.ReadLogicZero()
		for bit in self.bits:
			self.domain |= bit

		self.cube = m.IndicesToCube(intarray(self.index), len(self.index))

		# TODO eliminate?
		self.encodecache = [None for i in range(self.logical.range)]

		self.encoder = makeEncoder(self)		

	def __validateValue(self, value):
		assert isinstance(value, int) and value >= 0
		assert self.logical.contains(value)

	def __encode(self, value):
		self.__validateValue(value)

		encoded = m.ReadOne()
		
		for bit in self.bits:
			encoded &= bit if (value & 1) else ~bit
			value >>= 1

		return encoded

	def getBits(self, value, bits):
		self.__validateValue(value)
		
		for bit in self.bits:
			result = bit if (value & 1) else ~bit
			bits.append((result.NodeReadIndex(), result))
			value >>= 1

	def encode(self, value):
		self.__validateValue(value)

		# Cache the encoding, to speed up building the database.
		if not self.encodecache[value]:
			self.encodecache[value] = self.__encode(value)
			
		return self.encodecache[value]
		

	def getName(self):
		return self.logical.name

	def __repr__(self):
		return self.logical.name


	def makeCompare(self, op, other):
		assert op == '=='
		assert self.logical == other.logical

		compare = m.ReadOne()
		for a, b in zip(self.bits, other.bits):
			compare &= ~(a^b)
		return compare

	def buildEncoder(self, encoder):
		encoder.newField()

		for i, bit in enumerate(self.bits):
			encoder.newBit(2**i, bit)

class PhysicalStructure(object):
	def __init__(self, name, attributes):
		self.name 	= name
		self.attributes = attributes

		self.cube = m.ReadOne()
		for n, d in attributes:
			self.cube &= d.cube

		self.encoder = makeEncoder(self)


	def __validateValue(self, value):
		assert isinstance(value, tuple) and len(value) == len(self.attributes)

	
	def encode(self, value):
		self.__validateValue(value)
		encoded = m.ReadOne()

		for (aname, adomain), v in zip(self.attributes, value):
			encoded &= adomain.encode(v)
		return encoded

	def getBits(self, value, bits):
		self.__validateValue(value)
		for (aname, adomain), v in zip(self.attributes, value):
			adomain.getBits(v, bits)

	def getName(self):
		return self.name

	def __repr__(self):
		return "%s%s" % (self.name, repr(self.attributes))


	def makeCompare(self, op, other):
		assert op == '=='
		assert len(self.attributes) == len(other.attributes)

		compare = m.ReadOne()
		for (na, a), (nb, b) in zip(self.attributes, other.attributes):
			compare &= a.makeCompare(op, b)
		return compare

	def buildEncoder(self, encoder):
		for name, domain in self.attributes:
			domain.buildEncoder(encoder)

def makeEncoder(d):
	encoder = FlatEncoder()
	d.buildEncoder(encoder)
	encoder.finalize()
	return encoder


import time
import pycudd

class FlatEncoder(object):
	def __init__(self):
		self.table = []
		self.count = 0


	def newField(self):
		self.count += 1

	def newBit(self, value, bit):
		assert isinstance(value, (int, long))
		self.table.append((self.count-1, value, bit, ~bit))

	def finalize(self):
		self.table.sort(key=lambda e: e[2].NodeReadIndex(), reverse=True)
		self.array = pycudd.DdArray(len(self.table))


	def encode(self, flat):
		assert len(flat) == self.count

		# Using the array and the precalculated inverted bit
		# avoids the creation of temporary SWIG objects.
		# A big performance win.
		for i, (index, value, bit, ibit) in enumerate(self.table):
			result = bit if flat[index]&value else ibit
			self.array[i] = result

		return self.array.And()

		
