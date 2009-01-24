from __future__ import absolute_import

from _pystream import cfuncptr
from util import xtypes
from programIR.python import ast

exports = {}

def export(funcast):
	if isinstance(funcast, xtypes.FunctionType):
		name = funcast.func_name
	else:
		name = funcast.name

	assert not name in exports
	exports[name] = funcast
	return funcast

llastLUT = []
#attrPtr = []

ptrAST = []

foldLUT = {}
descriptiveLUT = {}

def llast(f):
	funcast = f()
	llastLUT.append(funcast)
	return funcast


_cfuncptr = cfuncptr

def cfuncptr(obj):
	try:
		return _cfuncptr(obj)
	except TypeError:
		raise TypeError, "Cannot get pointer from %r" % type(obj)

### Attachment functions ###

def attachAttrPtr(t, attr):
	assert isinstance(t, type), t
	assert isinstance(attr, str), attr

	meth = getattr(t, attr)
	ptr = cfuncptr(meth)

	def callback(funcast):
		assert isinstance(funcast, ast.Function), funcast
		ptrAST.append((ptr, funcast))
		return funcast
	return callback


def attachPtr(obj):
	ptr = cfuncptr(obj)
	def callback(funcast):
		assert isinstance(funcast, ast.Function), funcast
		ptrAST.append((ptr, funcast))
		return funcast
	return callback

def bindStubs(extractor):
	for ptr, funcast in ptrAST:
		extractor.attachStubToPtr(funcast, ptr)


def fold(func):
	def callback(funcast):
		assert isinstance(funcast, ast.Function), type(funcast)
		foldLUT[funcast.code] = func
		return funcast
	return callback

def descriptive(funcast):
	assert isinstance(funcast, ast.Function), type(funcast)
	descriptiveLUT[funcast.code] = True
	return funcast


##################
### High Level ###
##################

highLevelGlobals 	= {'method':xtypes.MethodType}
highLevelLUT 		= {}
objectReplacements	= []
attrReplacements	= []

from util import replaceGlobals

def highLevelStub(f):
	# Let the function use the common global dictionary.
	# Recreate the function with different globals.
	f = replaceGlobals(f, highLevelGlobals)

	# Register
	highLevelLUT[f.func_name] = f

	# Add to the common global dictionary
	highLevelGlobals[f.func_name] = f

	return f

### Attachment functions ###
def replaceObject(o):
	def callback(f):
		assert highLevelLUT[f.func_name] == f, "Must declare as high level stub before replacing."
		objectReplacements.append((o, f))
		return f
	return callback

def replaceObjects(extractor):
	for o, f in objectReplacements:
		extractor.replaceObject(o, f)


def replaceAttr(o, attr):
	def callback(f):
		assert highLevelLUT[f.func_name] == f, "Must declare as high level stub before replacing."
		attrReplacements.append((o, attr, f))
		return f
	return callback

def replaceAttrs(extractor):
	for o, attr, f in attrReplacements:
		extractor.replaceAttr(o, attr, f)
