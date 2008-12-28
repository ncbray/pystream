from __future__ import absolute_import

from _pystream import cfuncptr
from util import xtypes
from programIR.python.ast import Function

exports = {}

def export(ast):
	if isinstance(ast, xtypes.FunctionType):
		name = ast.func_name
	else:
		name = ast.name
		
	assert not name in exports
	exports[name] = ast
	return ast

llastLUT = []
#attrPtr = []

ptrAST = []

foldLUT = {}
descriptiveLUT = {}

def llast(f):
	ast = f()
	llastLUT.append(ast)
	return ast


### Attachment functions ###

def attachAttrPtr(t, attr):
	assert isinstance(t, type), t
	assert isinstance(attr, str), attr

	meth = getattr(t, attr)
	ptr = cfuncptr(meth)
	
	def callback(ast):
		assert isinstance(ast, Function), ast
		ptrAST.append((ptr, ast))
		return ast
	return callback


def attachPtr(obj):
	ptr = cfuncptr(obj)
	def callback(ast):
		assert isinstance(ast, Function), ast
		ptrAST.append((ptr, ast))
		return ast
	return callback

def bindStubs(extractor):
	for ptr, ast in ptrAST:
		extractor.attachStubToPtr(ast, ptr)


def fold(func):
	def callback(ast):
		foldLUT[ast] = func
		return ast
	return callback

def descriptive(ast):
	descriptiveLUT[ast] = True
	return ast


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
