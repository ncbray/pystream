from util import xtypes
from _pystream import cfuncptr

from common import opnames

from . constantfinder import findCodeReferencedObjects


from stubs import stubcollector, initalize
initalize() # HACK?

from stubs.stubcollector import exports, llastLUT # HACK


from programIR.python.program import ImaginaryObject, AbstractObject, Object
from programIR.python.ast import isPythonAST

TypeNeedsStub = (xtypes.MethodDescriptorType, xtypes.WrapperDescriptorType, xtypes.BuiltinFunctionType)
TypeNeedsHiddenStub = (xtypes.MethodDescriptorType, xtypes.WrapperDescriptorType)



def attachStubs(extractor):
	stubcollector.bindStubs(extractor)

from util.visitor import StandardVisitor

import util.xform

class LLASTTranslator(StandardVisitor):
	def __init__(self, extractor):
		self.extractor = extractor

	def default(self, node):
		util.xform.visitAllChildren(self.visit, node)

	def visitExisting(self, node):
		# Due to sloppy LLAst creation, sometimes the same Existing(..) node will be used mutiple times.
		# Therefore, we may encounter an alread mutated node.
		# TODO tighten standards for low-level Existing(...) reuse.
		if not isinstance(node.object, AbstractObject):
			result = self.extractor.getObject(node.object)
		else:
			# HACK should rewrite the AST, not mutate it.
			# Mutiple extractors may be created, (compiling seperate programs)
			# but all will use the stubs.
			result = self.extractor.getObject(node.object.pyobj)

		node.object = result


def translateLLAST(extractor, llastLUT):
	t = LLASTTranslator(extractor)
	for funcast in llastLUT:
		# HACK Mutates inplace, doesn't rewrite?
		# TODO rewrite
		t.walk(funcast.code.ast)
	return llastLUT



def setupLowLevel(extractor):
	# HACK will not be found until after mutate?
	extractor.getObject(exports['default__get__'])

	# Low level stubs need to be slightly modified
	llast = translateLLAST(extractor, llastLUT)

	# Stick low level stubs into the list of functions.
	extractor.desc.functions.extend(llast)

	attachStubs(extractor)



def attachCalls(extractor):
	desc = extractor.desc

	for obj in desc.objects:
		if isinstance(obj, Object):
			f = obj.pyobj
			if isinstance(f, TypeNeedsStub):
				try:
					ptr = cfuncptr(f)
					if ptr in extractor.pointerToStub:
						desc.bindCall(obj, extractor.pointerToStub[ptr])
				except TypeError:
					print "Cannot get pointer:", f

def attachCallToObj(extractor, desc, obj):
	# Hack for calling objects.
	if not extractor.getCall(obj):
		typedict = extractor.getTypeDict(obj.type)
		callstr = extractor.getObject('__call__')

		# HACK, does not chain the lookup?
		if callstr in typedict:
			func = extractor.getCall(typedict[callstr])
			if func:
				desc.callLUT[obj] = func

def mutateObjects(extractor):
	desc = extractor.desc

	# HACK for calling objects.
	for obj in desc.objects:
		attachCallToObj(extractor, desc, obj)



def finishExtraction(extractor):
	# Build the object -> function mapping
	# Done after the stubs are attached.
	#attachCalls(extractor)

	# If there isn't a entry in the callLUT, call the __call__ method instead.

	if False:
		mutateObjects(extractor)
