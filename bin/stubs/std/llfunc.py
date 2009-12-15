#@PydevCodeAnalysisIgnore

from __future__ import absolute_import

# TODO remove once type__call__ and method__call__ are made into a functions.
from language.python.ast import *

# HACK for highlevel functions?
from util.monkeypatch import xtypes
method   = xtypes.MethodType
function = xtypes.FunctionType

from .. stubcollector import stubgenerator

from util.asttools.origin import Origin


@stubgenerator
def makeLLFunc(collector):
	llast         = collector.llast
	llfunc        = collector.llfunc
	export        = collector.export
	highLevelStub = collector.highLevelStub
	replaceObject = collector.replaceObject
	replaceAttr   = collector.replaceAttr
	fold          = collector.fold
	staticFold    = collector.staticFold
	attachPtr     = collector.attachPtr

	##############
	### Object ###
	##############

	@attachPtr(object, '__init__')
	@llfunc(descriptive=True)
	def object__init__(self, *vargs):
		pass

	# TODO __getattr__ fallback?
	# Exported for the method finding optimization
	@export
	@attachPtr(object, '__getattribute__')
	@llfunc
	def object__getattribute__(self, field):
		selfType = load(self, 'type')
		typeDict = load(selfType, 'dictionary')

		getter = False
		setter = False
		exists = checkDict(typeDict, field)

		if exists:
			desc     = loadDict(typeDict, field)
			descDict = load(load(desc, 'type'), 'dictionary')
			getter   = checkDict(descDict, '__get__')
			setter   = checkDict(descDict, '__set__')

		# TODO support ShortCircutAnd?
		if getter:
			if setter:
				# It's a data descriptor
				return loadDict(descDict, '__get__')(desc, self, selfType)


		# TODO Get the self dictionary using the dictionary descriptor.
		# Requires get/set support
#		if checkDict(typeDict, '__dict__'):
#			dictDesc     = loadDict(typeDict, '__dict__')
#			dictDescType = load(dictDesc, 'type')
#			dictDescDict = load(dictDescType, 'dictionary')
#			selfDict     = loadDict(dictDescDict, '__get__')(dictDesc, self, selfType)

		# HACK load from low-level dictionary field instead of using get/set
		if check(self, 'dictionary'):
			selfDict = load(self, 'dictionary')
			if checkDict(selfDict, field):
				# Field in instance dictionary
				return loadDict(selfDict, field)

		# NOTE even if the previous return is always taken,
		# the following code will still be analyzed.
		# This is a weakness in the implementation that causes
		# false "unresolved constraints"
		# TODO analyze CFG instead of AST

		if getter:
			# It's a method descriptor
			return loadDict(descDict, '__get__')(desc, self, selfType)
		elif exists:
			# It's a class variable
			return desc
		else:
			# HACK not found?
			return desc


	@attachPtr(object, '__setattr__')
	@llfunc
	def object__setattr__(self, field, value):
		selfType     = load(self, 'type')
		selfTypeDict = load(selfType, 'dictionary')

		if checkDict(selfTypeDict, field):
			desc = loadDict(selfTypeDict, field)
			descTypeDict = load(load(desc, 'type'), 'dictionary')
			if checkDict(descTypeDict, '__set__'):
				loadDict(descTypeDict, '__set__')(desc, self, value)
				return
			elif check(self, 'dictionary'):
				storeDict(load(self, 'dictionary'), field, value)
				return
		elif check(self, 'dictionary'):
			# Duplicated to ensure the compiler sees it as mutually exclusive.
			storeDict(load(self, 'dictionary'), field, value)
			return

		# TODO exception



	############
	### Type ###
	############

	@attachPtr(object, '__new__')
	@llfunc
	def object__new__(cls, *vargs):
		return allocate(cls)

	@export  # HACK for intrinsics
	@attachPtr(type, '__call__')
	@llfunc
	def type__call__(self, *vargs):
		td = load(self, 'dictionary')

		new_method = loadDict(td, '__new__')
		inst = new_method(self, *vargs)

		init_method = loadDict(td, '__init__')
		init_method(inst, *vargs)

		return inst


	################
	### Function ###
	################

	# TODO create unbound methods if inst == None?
	# Replace object must be on outside?
	@export
	@replaceObject(xtypes.FunctionType.__get__)
	@highLevelStub
	def function__get__(self, inst, cls):
		return method(self, inst, cls)


	##############
	### Method ###
	##############

	@replaceAttr(xtypes.MethodType, '__init__')
	@highLevelStub
	def method__init__(self, func, inst, cls):
		self.im_func 	= func
		self.im_self 	= inst
		self.im_class 	= cls

	# The __call__ function for a bound method.
	# TODO unbound method?
	# High level, give or take argument uglyness.
	# Exported for method call optimization
	@export
	@attachPtr(xtypes.MethodType, '__call__')
	@llast
	def method__call__():
		internal_self = Local('internal_self')
		self = Local('self')

		im_self = Local('im_self')
		im_func = Local('im_func')
		temp 	= Local('temp')
		retp = Local('internal_return')

		vargs = Local('vargs')

		b = Suite()

		# TODO analysis does not terminate if  generic "GetAttr" is used?
		b.append(collector.loadAttribute(self, xtypes.MethodType, 'im_self', im_self))
		b.append(collector.loadAttribute(self, xtypes.MethodType, 'im_func', im_func))
#		b.append(Assign(GetAttr(self, collector.existing('im_self')), im_self))
#		b.append(Assign(GetAttr(self, collector.existing('im_func')), im_func))


		b.append(Assign(Call(im_func, [im_self], [], vargs, None), [temp]))
		b.append(Return([temp]))

		name = 'method__call__'
		code = Code(name, CodeParameters(internal_self, [self], ['self'], [], vargs, None, [retp]), b)

		code.rewriteAnnotation(origin=Origin(name, __file__, None, None))
		return code


#	@export
#	@attachPtr(xtypes.MethodType, '__call__')
#	@llfunc
#	def method__call__(self, *vargs):
#		im_func = self.im_func
#		im_self = self.im_self
#		return im_func(im_self, *vargs)

	# Getter for function, returns method.
	@export
	@attachPtr(xtypes.MethodDescriptorType, '__get__')
	@attachPtr(xtypes.WrapperDescriptorType, '__get__') # HACK?
	@llfunc
	def methoddescriptor__get__(self, inst, cls):
		return method(load(self, 'function'), inst, cls)


	#########################
	### Member Descriptor ###
	#########################

	# Used for a slot data getter.
	# Low level, gets slot attribute.
	@attachPtr(xtypes.MemberDescriptorType, '__get__')
	@llfunc
	def memberdescriptor__get__(self, inst, cls):
		return loadAttr(inst, load(self, 'slot'))

	# For data descriptors, __set__
	# Low level, involves slot manipulation.
	@attachPtr(xtypes.MemberDescriptorType, '__set__')
	@llfunc
	def memberdescriptor__set__(self, inst, value):
		storeAttr(inst, load(self, 'slot'), value)


	###########################
	### Property Descriptor ###
	###########################

	# TODO fget is None?
	@attachPtr(property, '__get__')
	@llfunc
	def property__get__(self, inst, owner):
		return self.fget(inst)

	# TODO fset is None?
	@attachPtr(property, '__set__')
	@llfunc
	def property__set__(self, inst, value):
		return self.fset(inst, value)

	#########################
	### Builtin functions ###
	#########################

	# TODO full implementation requires loop unrolling?
	@fold(issubclass)
	@attachPtr(issubclass)
	@llfunc(descriptive=True)
	def issubclass_stub(cls, clsinfo):
		return allocate(bool)

	@attachPtr(isinstance)
	@llfunc
	def isinstance_stub(obj, classinfo):
		return issubclass(load(obj, 'type'), classinfo)


	# TODO multiarg?
	@export # HACK for intrinsics
	@staticFold(max)
	@attachPtr(max)
	@llfunc
	def max_stub(a, b):
		return b if a < b else a

	# TODO multiarg?
	@staticFold(min)
	@attachPtr(min)
	@llfunc
	def min_stub(a, b):
		return a if a < b else b

