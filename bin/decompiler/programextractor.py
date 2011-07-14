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

from __future__ import absolute_import

import collections

import language.python.program as program

from . bytecodedecompiler import decompile
from . errors import IrreducibleGraphException

# Cached "getter" w/ processing queue and "valid" flag?

import inspect

from . import errors

import sys
import dis
import util

from application.errors import TemporaryLimitation, InternalError

from util.monkeypatch import xtypes

from _pystream import cfuncptr


class FieldNotFoundType(object):
	pass
FieldNotFound = FieldNotFoundType()

def type_fields(t):
	fields = set()
	for cls in inspect.getmro(t):
		fields.update(cls.__dict__.iterkeys())
	return fields

def type_lookup(t, field):
	for cls in inspect.getmro(t):
		d = cls.__dict__
		if field in d:
			return d[field]

	return FieldNotFound

def flatTypeDict(t):
	fields = type_fields(t)

	out = {}
	for field in fields:
		result = type_lookup(t, field)
		assert result is not FieldNotFound
		out[field] = result
	return out


class Extractor(object):
	def __init__(self, compiler, verbose=True):
		self.compiler = compiler # Circular reference, ugly!

		self.types 	= {}
		self.objcache 	= {}

		self.pointerToObject = {}
		self.pointerToStub   = {}

		# ptr -> list(obj) where cfuncptr(obj) == ptr
		self.registeredPointers = collections.defaultdict(list)

		self.attrLUT = collections.defaultdict(dict)

		self.codeLUT = {}

		self.complete = collections.defaultdict(lambda: False)
		self.queue = collections.deque()

		self.constpool = collections.defaultdict(dict)

		# What we're building.
		self.desc = program.ProgramDescription()

		self.verbose = verbose


		self.lazy = True


		# Status
		self.errors = 0
		self.failiures = 0
		self.functions = 0
		self.builtin = 0
		self.badopcodes = collections.defaultdict(lambda: 0)

		# Used for debugging, prevents new object from being extracted when set to true.
		self.finalized = False

		self.typeDictCache = {}
		self.typeDictType = {}

		self.initalizeObjects()


		self.getsetMember = set()
		self.getsetMember.add(xtypes.FunctionType.__dict__['func_defaults'])

	def flatTypeDict(self, cls):
		assert isinstance(cls, type)

		if cls not in self.typeDictCache:
			self.typeDictCache[cls] = flatTypeDict(cls)

		return self.typeDictCache[cls]


	def makeImaginary(self, name, t, preexisting):
		obj = program.ImaginaryObject(name, t, preexisting)
		self.desc.objects.append(obj)
		return obj

	def makeImaginaryFunctionObject(self, name):
		t = self.__getObject(xtypes.BuiltinFunctionType)
		return self.makeImaginary(name, t, True)

	def makeHiddenFunction(self, parent, ptr):
		if ptr not in self.pointerToObject:
			if isinstance(ptr, tuple):
				name = "stub_%d_%d" % ptr
			else:
				name = "stub_%d" % ptr
			obj = self.makeImaginaryFunctionObject(name)
			self.registerPointer(ptr, obj)
			self.pointerToObject[ptr] = obj
		else:
			obj = self.pointerToObject[ptr]

		parent.addLowLevel(self.desc.functionNameObj, obj)
		return obj

	# Given a function pointer and a stub, link the pointer to the stub.
	# Only do the attachment the first time the pointer is encountered.
	def attachStubToPtr(self, stub, ptr):
		if not ptr in self.pointerToStub:
			self.pointerToStub[ptr] = stub

			for obj in self.registeredPointers[ptr]:
				self.desc.bindCall(obj, stub)
		else:
			assert self.pointerToStub[ptr] == stub, (stub, self.pointerToStub[ptr])


	def replaceObject(self, original, replacement):
		assert not id(original) in self.objcache, original
		self.objcache[id(original)] = self.__getObject(replacement)

	def replaceAttr(self, obj, attr, replacement):
		assert isinstance(obj, type), obj
		assert isinstance(attr, str), attr

		assert obj not in self.complete # It hasn't be processed, yet.

		self.attrLUT[id(obj)][attr] = replacement

	def replaceCode(self, obj, code):
		assert not isinstance(obj, program.AbstractObject), obj
		assert not id(obj) in self.objcache, obj
		self.codeLUT[id(obj)] = code

	def initalizeObjects(self):
		# HACK Prevents uglyness by masking the module dictionary.  This prevents leakage.
		if not self.lazy:
			self.replaceObject(sys.modules, {})

		# Strings for mutating the image
		self.desc.functionNameObj = self.getObject('function')
		self.desc.slotObj         = self.getObject('slot')
		self.desc.nameObj         = self.getObject('__name__')
		self.desc.objClassObj     = self.getObject('__objclass__')

		self.desc.dict__Name      = self.getObject('__dict__')
		self.desc.dictionaryName  = self.getObject('dictionary')


	def getCanonical(self, o):
		if type(o) in xtypes.ConstantTypes:
			if not o in self.constpool[type(o)]:
				self.constpool[type(o)][o] = o
			else:
				o = self.constpool[type(o)][o]
		return o



	def contains(self, o):
		return id(self.getCanonical(o)) in self.objcache

	def __contains__(self, o):
		return self.contains(o)

	def ensureLoaded(self, o):
		assert isinstance(o, program.AbstractObject), o

		# When lazy loading is used, this function needs to be defined.
		if self.lazy:
			if isinstance(o, program.Object) and not self.complete[o]:
				self.processObject(o)
				assert self.complete[o]

	def getCall(self, o):
		self.ensureLoaded(o)
		return self.desc.callLUT.get(o)

	def getObject(self, o, t=False):
		assert type(o).__dict__ not in self, o

		result = self.__getObject(o, t)
		return result

	def getInstance(self, typeobj):
		typeobj = self.getObject(typeobj, True)
		self.ensureLoaded(typeobj)
		return typeobj.abstractInstance()


	def getObjectCall(self, func):
		fobj = self.getObject(func)
		self.ensureLoaded(fobj)
		code = self.getCall(fobj)
		return fobj, code


	# Returns the slot name for the attribute.
	def getObjectAttr(self, obj, name):
		for t in inspect.getmro(obj.type.pyobj):
			attr = t.__dict__.get(name)
			if attr:
				attrName = self.getObject(self.compiler.slots.uniqueSlotName(attr))
				return ('Attribute', attrName)

		assert False, "%r does not have attribute %r" % (obj, name)



	def __getObject(self, o, t=False):
		assert not isinstance(o, program.AbstractObject), o

		o = self.getCanonical(o)

		if not self.contains(o):
			assert not self.finalized, o

			# Create the object
			obj = program.Object(o)

			# Lookup table, by object ID.
			self.objcache[id(o)] = obj

			# A list of created objects
			self.desc.objects.append(obj)

			if not self.lazy:
				# Put object in processing queue.
				# Give priority to types, in reverse order.
				if t:
					self.queue.appendleft(obj)
				else:
					self.queue.append(obj)

##			# Must be after caching, as types may recurse.
##			self.initalizeObject(obj)

			return obj
		else:
			return self.objcache[id(o)]

	def process(self):
		if self.lazy:
			return

		assert not self.queue or not self.finalized

		while self.queue:
			obj = self.queue.popleft()
			self.processObject(obj)

		#self.printStatus()

		# Invariants
		assert not self.queue
##		for obj in self.objcache.itervalues():
##			assert self.complete[obj], obj


	def finalize(self):
		assert not self.finalized
		self.finalized = True

	def unfinalize(self):
		assert self.finalized
		self.finalized = False

	def printStatus(self):
		print "Found %d objects." % len(self.objcache)
		print "%d python functions." % self.functions
		print "%d builtin functions." % self.builtin

		print "%d errors." % self.errors
		print "%d failiures." % self.failiures

		self.printBadOpcodes()

	def printBadOpcodes(self):
		if len(self.badopcodes):
			print "=== BAD OPCODES ==="
			p = self.badopcodes.items()
			p.sort(key=lambda e: e[1], reverse=True)
			for op, count in p:
				print op, count


	def defer(self, obj):
		self.queue.append(obj)

	def dictSlotForObj(self, pyobj):
		assert not isinstance(pyobj, program.AbstractObject)
		flat = self.flatTypeDict(type(pyobj))
		if '__dict__' in flat:
			return self.compiler.slots.uniqueSlotName(flat['__dict__'])
		else:
			return None

	def registerPointer(self, ptr, obj):
		if ptr in self.pointerToStub:
			self.desc.bindCall(obj, self.pointerToStub[ptr])
		self.registeredPointers[ptr].append(obj)

	def postProcessMutate(self, obj):
		pyobj = obj.pyobj

		# Create a low-level slot for the dictionary, if one exists.
		# Note that for type objects, this is done earlier.
		if not isinstance(pyobj, type):
			mangledDictName = self.dictSlotForObj(pyobj)
			if mangledDictName:
				mangledDictNameObj = self.__getObject(mangledDictName)
				if mangledDictNameObj in obj.slot:
					obj.addLowLevel(self.desc.dictionaryName, obj.slot[mangledDictNameObj])

		# No function pointers, so C function pointers are transformed into a hidden function object.
		if isinstance(pyobj, xtypes.TypeNeedsHiddenStub):
			self.makeHiddenFunction(obj, cfuncptr(pyobj))

		# No internal pointers, so member descriptors need to have a "slot pointer" added
		if isinstance(pyobj, xtypes.MemberDescriptorType):
			# It's a slot descriptor.
			# HACK there's no such thing as a "slot pointer", so use a unique string
			mangledNameObj = self.__getObject(self.compiler.slots.uniqueSlotName(pyobj))
			obj.addLowLevel(self.desc.slotObj, mangledNameObj)

		# Requires a C function pointer.
		if isinstance(pyobj, xtypes.TypeNeedsStub):
			try:
				ptr = cfuncptr(pyobj)
				self.registerPointer(ptr, obj)
			except TypeError:
				print "Cannot get pointer:", pyobj

	def canProcess(self, obj):
		return True

	def initalizeObject(self, obj):
		tob = self.__getObject(type(obj.pyobj), True)
		obj.allocateDatastructures(tob)
		obj.addLowLevel(self.__getObject('type'), tob)

	def processObject(self, obj):
		pyobj = obj.pyobj

		assert not self.complete[obj], obj

		if self.canProcess(obj):
			# Must be after caching, as types may recurse.
			self.initalizeObject(obj)


			if isinstance(pyobj, xtypes.FunctionType):
				self.handleFunction(obj)
			elif isinstance(pyobj, xtypes.BuiltinFunctionType):
				self.handleBuiltinFunction(obj)
			elif isinstance(pyobj, type):
				self.handleType(obj)
			else:
				self.handleObject(obj)

			self.postProcessMutate(obj)

			self.complete[obj] = True
		else:
			self.defer(obj)


	def getTypeDict(self, obj):
		assert isinstance(obj.pyobj, type), obj.pyobj
		self.ensureLoaded(obj)
		dictobj = obj.lowlevel[self.desc.dictionaryName]
		self.ensureLoaded(dictobj)
		return dictobj.dictionary

	def handleLowLevel(self, obj):
		# Low level slots aren't directly visible, so we need to explicitly get them.
		pyobj = obj.pyobj
		if isinstance(pyobj, tuple):
			obj.addLowLevel(self.__getObject('length'), self.__getObject(len(pyobj)))

	# Object may have fixed slots.  Search for them.
	def handleSlots(self, obj):
		pyobj = obj.pyobj

		flat = self.flatTypeDict(type(pyobj))

		# Relies on type dictionary being flattened.
		for name, member in flat.iteritems():
			assert not isinstance(name, program.AbstractObject), name
			assert not isinstance(member, program.AbstractObject), member

			# TODO Directly test for slot wrapper?
			# TODO slot wrapper for methods?
			isMember = inspect.ismemberdescriptor(member)

			# HACK some getsets may as well be members
			isMember |= inspect.isgetsetdescriptor(member) and member in self.getsetMember

			if isMember:
				try:
					value = member.__get__(pyobj, type(pyobj))
				except:
					print "Error getting attribute %s" % name
					print "obj", pyobj
					for k, v in inspect.getmembers(pyobj):
						print '\t', k, repr(v)
					raise
				mangledName = self.compiler.slots.uniqueSlotName(member)
				obj.addSlot(self.__getObject(mangledName), self.__getObject(value))


	# Object my have an arbitrary dictionary.
	def handleObjectDict(self, obj):
		# HACK Promote dictionary items to slots.  Should undo.
		if hasattr(obj.pyobj, '__dict__'):
			self.__handleObjectDict(obj, obj.pyobj.__dict__)

	def __handleObjectDict(self, obj, d):
		for k, v in d.iteritems():
			# HACK addSlot is unsound?
			nameObj = self.__getObject(k)
			valueObj = self.__getObject(v)
			obj.addSlot(nameObj, valueObj)


	def handleContainer(self, obj):
		if isinstance(obj.pyobj, (dict, xtypes.DictProxyType)):
			lut = {}

			# If this is a type dict, some attributes may be replaced.
			if obj in self.typeDictType:
				cls = self.typeDictType[obj]
				clsid = id(cls.pyobj)
				if clsid in self.attrLUT:
					lut = self.attrLUT[clsid]

			keys = set(obj.pyobj.iterkeys())
			keys.update(lut.iterkeys())

			for k in keys:
				v = obj.pyobj.get(k)
				v = lut.get(k, v) # Replace the value if needed.
				obj.addDictionaryItem(self.__getObject(k), self.__getObject(v))
		elif isinstance(obj.pyobj, (set, frozenset)):
			for po in obj.pyobj:
				o = self.__getObject(po)
				obj.addDictionaryItem(o, o)
		elif isinstance(obj.pyobj, (tuple, list)):
			for i, v in zip(range(len(obj.pyobj)), obj.pyobj):
				indexObj = self.__getObject(i)
				obj.addArrayItem(indexObj, self.__getObject(v))


	def handleObject(self, obj):
		pyobj = obj.pyobj

		self.handleLowLevel(obj)
		self.handleSlots(obj)
		self.handleObjectDict(obj)
		self.handleContainer(obj)


	def handleType(self, obj):
		# Flatten the type dictionary and add a low-level pointer.
		# TODO point type.__dict__ slot getter to this slot?
		flat = self.flatTypeDict(obj.pyobj)
		flatObj = self.__getObject(flat)

		# This is so the mutator knows it's dealing with a type dictionary
		self.typeDictType[flatObj] = obj


		# All type objects have flattened dictionaries.
		obj.addLowLevel(self.desc.dictionaryName, flatObj)



		pyobj = obj.pyobj

		for t in inspect.getmro(pyobj):
			self.__getObject(t, True)

		self.types[id(obj)] = obj

		# Slot wrapper
		# member
		# attribute?
		# GetSet

		obj.typeinfo = program.TypeInfo()


		# MUTATE
		# Create abstract instance for the type.
		obj.typeinfo.abstractInstance = self.makeImaginary("%s_instance" % pyobj.__name__, obj, False)

		# HACK assumes standard getattribute function?
		assert hasattr(obj.pyobj, '__dict__')

		self.handleObject(obj)


	def handleBuiltinFunction(self, obj):
		func = obj.pyobj
		self.builtin += 1


	def handleFunction(self, obj):
		self.handleObject(obj)

		replace = self.codeLUT.get(id(obj.pyobj))
		if replace:
			self.desc.bindCall(obj, replace)
		else:
			function = self.decompileFunction(obj.pyobj)

			if function != None:
				self.desc.functions.append(function)
				self.desc.bindCall(obj, function)


	def decompileFunction(self, func, trace=False, ssa=True, descriptive=False):
		function = None

		try:
			function = decompile(self.compiler, func, trace=trace, ssa=ssa, descriptive=descriptive)
		except IrreducibleGraphException:
			raise Exception, ("Cannot reduce graph for %s" % repr(func))
		except errors.UnsupportedOpcodeError, e:
			if self.verbose: print "ERROR decompiling %s. %r" % (repr(func), e)
			if False:
				dis.dis(func)
			self.badopcodes[e.args[0]] += 1
			self.errors += 1
		except InternalError, e:
			if self.verbose: print "Internal Error: %r prevented the decompilation of %s." % (e, repr(func))
			self.failiures += 1
		except TemporaryLimitation, e:
			if self.verbose: print "Temporary limitation: %r prevented the decompilation of %s." % (e, repr(func))
			self.failiures += 1
		except Exception, e:
			print "Unhandled %s prevented the decompilation of %s." % (type(e).__name__, repr(func))
			self.failiures += 1
			raise
		else:
			self.functions += 1

		return function


from stubs import makeStubs

def extractProgram(compiler, prgm):
	compiler.extractor = Extractor(compiler)

	# Create stub functions
	makeStubs(compiler)

	prgm.interface.translate(compiler.extractor)
