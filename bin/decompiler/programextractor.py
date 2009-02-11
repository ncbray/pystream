from __future__ import absolute_import

import collections

import programIR.python.program as program

from stubs import makeStubs

from . decompiler import decompile
from . errors import IrreducibleGraphException

# Cached "getter" w/ processicng queue and "valid" flag?

import inspect

from . import errors

import sys
import dis
import util

from common.errors import TemporaryLimitation, InternalError

import optimization.simplify

from util import xtypes

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

def translateEntryPoint(extractor, module, name, args):
	name = extractor.getObject(name)

	extractor.ensureLoaded(module)

	assert name in module.slot, name
	fobj = module.slot[name] # Is this correct?  It might be in the dictionary...
	# TODO just get from the pyobj?

	extractor.ensureLoaded(fobj)
	func = extractor.getCall(fobj)

	argobjs  = [arg.getObject(extractor) for arg in args]
	return func, fobj, argobjs


def translateEntryPoints(extractor, module, rawEntryPoints):
	return [translateEntryPoint(extractor, module, name, args) for name, args in rawEntryPoints]

class Extractor(object):
	def __init__(self, verbose=True):
		self.types 	= {}
		self.objcache 	= {}

		self.pointerToObject = {}
		self.pointerToStub   = {}

		# ptr -> list(obj) where cfuncptr(obj) == ptr
		self.registeredPointers = collections.defaultdict(list)

		self.attrLUT = collections.defaultdict(dict)

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

		self.stubs = makeStubs(self)
		self.initalizeObjects()



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
			obj = self.makeImaginaryFunctionObject("stub_%d" % ptr)
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
			assert self.pointerToStub[ptr] == stub, stub


	def replaceObject(self, original, replacement):
		assert not id(original) in self.objcache, original
		self.objcache[id(original)] = self.__getObject(replacement)

	def replaceAttr(self, obj, attr, replacement):
		assert isinstance(obj, type), obj
		assert isinstance(attr, str), attr

		assert obj not in self.complete # It hasn't be processed, yet.

		self.attrLUT[id(obj)][attr] = replacement

	def initalizeObjects(self):
		# HACK Prevents uglyness by masking the module dictionary.  This prevents leakage.
		if not self.lazy:
			self.replaceObject(sys.modules, {})

		# Always need it, but might miss it in some cases (interpreter has internal refernece).
		self.__getObject(__builtins__)

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
		# When lazy loading is used, this function needs to be defined.
		if self.lazy:
			if isinstance(o, program.Object) and not self.complete[o]:
				self.processObject(o)
				assert self.complete[o]

	def getCall(self, o):
		self.ensureLoaded(o)

		if o.type.pyobj in ((xtypes.FunctionType,)+xtypes.TypeNeedsStub):
			return self.desc.callLUT.get(o)


		if o not in self.desc.callLUT:
			self.desc.callLUT[o] = None # Prevent recursion.

			typedict = self.getTypeDict(o.type)
			callstr = self.getObject('__call__')

			# HACK, does not chain the lookup?
			if callstr in typedict:
				callobj = typedict[callstr]
				assert callobj is not o, "Cycle when looking for call: %r" % o
				func = self.getCall(callobj)
				if func:
					self.desc.callLUT[o] = func

		return self.desc.callLUT.get(o)

	def getObject(self, o, t=False):
		assert type(o).__dict__ not in self, o

		result = self.__getObject(o, t)
		return result

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
			return util.uniqueSlotName(flat['__dict__'])
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
			mangledNameObj = self.__getObject(util.uniqueSlotName(pyobj))
			obj.addLowLevel(self.desc.slotObj, mangledNameObj)

		# Requires a C function pointer.
		if isinstance(pyobj, xtypes.TypeNeedsStub):
			try:
				ptr = cfuncptr(pyobj)
				self.registerPointer(ptr, obj)
			except TypeError:
				print "Cannot get pointer:", f

		if pyobj is int or pyobj is long:
			dict = obj.lowlevel[self.desc.dictionaryName]
			self.ensureLoaded(dict)

			for op in ('eq', 'ne', 'lt', 'le', 'ge', 'gt'):
				s = '__%s__' % op
				sObj = self.__getObject(s)
				fObj = self.makeImaginaryFunctionObject(s)
				self.desc.bindCall(fObj, self.stubs.exports['int_rich_compare'])
				dict.addDictionaryItem(sObj, fObj)

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
			if inspect.ismemberdescriptor(member):
				try:
					mangledName = util.uniqueSlotName(member)
					value = member.__get__(pyobj, type(pyobj))
					obj.addSlot(self.__getObject(mangledName), self.__getObject(value))
				except:
					print "Error getting attribute?"
					print "obj", pyobj
					for k, v in inspect.getmembers(member):
						print '\t', k, v
					raise


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

			for k, v in obj.pyobj.iteritems():
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

		function = self.decompileFunction(obj.pyobj)

		if function != None:
			self.desc.functions.append(function)
			self.desc.bindCall(obj, function)


	def decompileFunction(self, func, trace=False, ssa=True):
		function = None

		try:
			function = decompile(func, self, trace=trace, ssa=ssa)
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


def extractProgram(moduleName, module, rawEntryPoints):
	extractor = Extractor()

	# Seed the search
	moduleObj = extractor.getObject(module)

	# Get the entry points.
	entryPoints = translateEntryPoints(extractor, moduleObj, rawEntryPoints)

	return extractor, entryPoints
