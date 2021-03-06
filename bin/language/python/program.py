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

# Describes the program "image" in memory.

import collections
import inspect
import types

# HACK types are considered constant
# This allows issubclass(type, type) to be folded
# Types are almost constant, however, by fiat.
constantTypes = set((float, int, long, str, bool, type(None), type, types.CodeType))
lexicalConstantTypes = set((float, int, long, str, bool, type(None)))
poolableTypes = set((float, int, long, str, bool))

class ProgramDecl(object):
	__slots__ = ()

class TypeInfo(object):
	__slots__ = 'abstractInstance'
	def __init__(self):
		self.abstractInstance = None

class AbstractObject(ProgramDecl):
	__slots__ = 'type', '__weakref__'

	def isType(self):
		return False

	def isAbstract(self):
		return self.type.typeinfo.abstractInstance == self

	def isConcrete(self):
		return not self.isAbstract()

	def isConstant(self):
		return False

	def isLexicalConstant(self):
		return False

	def isUnique(self):
		return self.isPreexisting() and self.pythonType() not in poolableTypes


def isConstant(pyobj):
	if isinstance(pyobj, (tuple, frozenset)):
		for item in pyobj:
			if not isConstant(item):
				return False
		return True
	else:
		return type(pyobj) in constantTypes


def isLexicalConstant(pyobj):
	if isinstance(pyobj, (tuple, frozenset)):
		for item in pyobj:
			if not isLexicalConstant(item):
				return False
		return True
	else:
		return type(pyobj) in lexicalConstantTypes


class Object(AbstractObject):
	__slots__ = 'pyobj', 'typeinfo', 'slot', 'array', 'dictionary', 'lowlevel'

	def __init__(self, pyobj):
		assert not isinstance(pyobj, ProgramDecl), "Tried to wrap a wrapper."
		self.pyobj 	= pyobj

	def allocateDatastructures(self, type_):
		# Even the simple ones are set lazily,
		# so early accesses become hard errors.
		self.type       = type_
		self.typeinfo   = None
		self.slot 	= {}
		self.array 	= {}
		self.dictionary = {}
		self.lowlevel	= {}

	def isPreexisting(self):
		return True

	def isConstant(self):
		return isConstant(self.pyobj)

	def isLexicalConstant(self):
		return isLexicalConstant(self.pyobj)

	def isType(self):
		return isinstance(self.pyobj, type)

	def abstractInstance(self):
		assert self.isType()
		return self.typeinfo.abstractInstance

	def addSlot(self, name, obj):
		assert isinstance(name, Object), name
		assert isinstance(name.pyobj, str), name
		assert isinstance(obj, AbstractObject), obj
		self.slot[name] = obj

	def addDictionaryItem(self, key, value):
		assert isinstance(key, Object), key
		assert isinstance(value, AbstractObject), value
		self.dictionary[key] = value

	def addArrayItem(self, index, value):
		assert isinstance(index, Object), index
		assert isinstance(index.pyobj, int), index
		assert isinstance(value, AbstractObject), value
		self.array[index] = value

	def addLowLevel(self, name, obj):
		assert isinstance(name, Object), name
		assert isinstance(name.pyobj, str), name
		assert isinstance(obj, AbstractObject), obj
		self.lowlevel[name] = obj

	def getDict(self, fieldtype):
		if fieldtype == 'LowLevel':
			d = self.lowlevel
		elif fieldtype == 'Attribute':
			d = self.slot
		elif fieldtype == 'Array':
			d = self.array
		elif fieldtype == 'Dictionary':
			d = self.dictionary
		else:
			assert False, fieldtype
		return d

	def __repr__(self):
		if isinstance(self.pyobj, dict):
			# Simplifies large, global dictionaries.
			r = "dict"+repr(tuple(self.pyobj.iterkeys()))
		else:
			r = repr(self.pyobj)

		if len(r) > 40:
			return "%s(%s...)" % (type(self).__name__, r[:37])
		else:
			return "%s(%s)" % (type(self).__name__, r)

	def pythonType(self):
		# self.type may be uninitialized, so go directly to the pyobj.
		return type(self.pyobj)


class ImaginaryObject(AbstractObject):
	__slots__ = 'name', 'preexisting'
	def __init__(self, name, t, preexisting):
		assert t.isType()
		self.name = name
		self.type = t
		self.preexisting = preexisting

	def __repr__(self):
		return "%s(%s)" % (type(self).__name__, self.name)

	def isPreexisting(self):
		# HACK imaginary objects may be prexisting
		# For example: hidden function stubs.
		return self.preexisting

	def pythonType(self):
		return self.type.pyobj

# TODO create unique ID for hashable objects.
# Collect IDs from given type into abstract object.  (Should be a continguous range?)

# Namespaces (dicts)
# Objects
# Function
# Types - objects w/object model info?

def getPrev(t):
	mro = inspect.getmro(t)

	if len(mro) > 1:
		return mro[1]
	else:
		return t

class ProgramDescription(object):
	def __init__(self):
		self.objects 	= []
		self.functions 	= []
		self.callLUT 	= {}
		self.origin     = {}


	def clusterObjects(self):
		children 	= collections.defaultdict(set)
		instances 	= collections.defaultdict(list)

		for obj in self.objects:
			assert obj.type != None, obj
			t = obj.type.pyobj

			instances[t].append(obj)

			prev = getPrev(t)

			while not t in children[prev] and t != prev:
				children[prev].add(t)
				t = prev
				prev = getPrev(t)

		count = len(self.objects)
		self.objects = []
		self.addChildren(children, instances, object)
		assert len(self.objects) == count

	def addChildren(self, c, i, t, tabs=''):
		#print tabs, t, len(i[t])
		self.objects.extend(i[t])
		for child in c[t]:
			self.addChildren(c, i, child, tabs+'\t')

	def bindCall(self, obj, func):
		assert isinstance(obj, AbstractObject), obj
		assert not isinstance(func, AbstractObject), func
		assert obj not in self.callLUT, obj
		self.callLUT[obj] = func
		self.origin[obj]  = func.annotation.origin
