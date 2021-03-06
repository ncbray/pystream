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

from util.asttools.annotation import *
from util.asttools.origin import Origin

def codeOrigin(code, line=None, col=None):
	if line is None: line = code.co_firstlineno
	return Origin(code.co_name, code.co_filename, line, col)

def functionOrigin(func, line=None, col=None):
	return codeOrigin(func.func_code, line, col)

class Annotation(object):
	__slots__ = ()

class CodeAnnotation(Annotation):
	__slots__ = ['contexts',
		'descriptive', 'primitive',
		'staticFold', 'dynamicFold',
		'origin',
		'live', 'killed',
		'codeReads', 'codeModifies', 'codeAllocates',
		'lowered', 'runtime', 'interpreter']

	def __init__(self, contexts, descriptive, primitive, staticFold, dynamicFold, origin, live, killed, codeReads, codeModifies, codeAllocates, lowered, runtime, interpreter):
		self.contexts    = tuple(contexts) if contexts is not None else None
		self.descriptive = descriptive
		self.primitive   = primitive
		self.staticFold  = staticFold
		self.dynamicFold = dynamicFold
		self.origin      = origin
		self.live        = live
		self.killed      = killed
		self.codeReads     = codeReads
		self.codeModifies  = codeModifies
		self.codeAllocates = codeAllocates
		self.lowered     = lowered
		self.runtime     = runtime
		self.interpreter = interpreter

	def rewrite(self, contexts=noMod,
			descriptive=noMod, primitive=noMod,
			staticFold=noMod, dynamicFold=noMod,
			origin=noMod,
			live=noMod, killed=noMod,
			codeReads=noMod, codeModifies=noMod, codeAllocates=noMod, lowered=noMod,
			runtime=noMod, interpreter=noMod):
		if contexts    is noMod: contexts    = self.contexts
		if descriptive is noMod: descriptive = self.descriptive
		if primitive   is noMod: primitive   = self.primitive
		if staticFold  is noMod: staticFold  = self.staticFold
		if dynamicFold is noMod: dynamicFold = self.dynamicFold
		if origin      is noMod: origin      = self.origin
		if live        is noMod: live        = self.live
		if killed      is noMod: killed      = self.killed
		if codeReads     is noMod: codeReads     = self.codeReads
		if codeModifies  is noMod: codeModifies  = self.codeModifies
		if codeAllocates is noMod: codeAllocates = self.codeAllocates
		if lowered is noMod: lowered = self.lowered
		if runtime is noMod: runtime = self.runtime
		if interpreter is noMod: interpreter = self.interpreter

		return CodeAnnotation(contexts, descriptive, primitive, staticFold, dynamicFold, origin, live, killed, codeReads, codeModifies, codeAllocates, lowered, runtime, interpreter)

	def contextSubset(self, remap, invokeMapper=None):
		contexts = [self.contexts[i] for i in remap]
		live     = remapContextual(self.live, remap)
		killed   = remapContextual(self.killed, remap)

		codeReads     = remapContextual(self.codeReads, remap)
		codeModifies  = remapContextual(self.codeModifies, remap)
		codeAllocates = remapContextual(self.codeAllocates, remap)

		return self.rewrite(contexts=contexts, live=live, killed=killed, codeReads=codeReads, codeModifies=codeModifies, codeAllocates=codeAllocates)

class OpAnnotation(Annotation):
	__slots__ = 'invokes', 'opReads', 'opModifies', 'opAllocates', 'reads', 'modifies', 'allocates', 'origin'

	def __init__(self, invokes, opReads, opModifies, opAllocates, reads, modifies, allocates, origin):
		self.invokes     = invokes
		self.opReads     = opReads
		self.opModifies  = opModifies
		self.opAllocates = opAllocates
		self.reads       = reads
		self.modifies    = modifies
		self.allocates   = allocates
		self.origin      = origin

	def rewrite(self, invokes=noMod, opReads=noMod, opModifies=noMod, opAllocates=noMod, reads=noMod, modifies=noMod, allocates=noMod, origin=noMod):
		if invokes     is noMod: invokes     = self.invokes
		if opReads     is noMod: opReads     = self.opReads
		if opModifies  is noMod: opModifies  = self.opModifies
		if opAllocates is noMod: opAllocates = self.opAllocates
		if reads       is noMod: reads       = self.reads
		if modifies    is noMod: modifies    = self.modifies
		if allocates   is noMod: allocates   = self.allocates
		if origin      is noMod: origin      = self.origin

		return OpAnnotation(invokes, opReads, opModifies, opAllocates, reads, modifies, allocates, origin)

	def contextSubset(self, remap, invokeMapper=None):
		invokes     = remapContextual(self.invokes,     remap, invokeMapper)
		opReads     = remapContextual(self.opReads,     remap)
		opModifies  = remapContextual(self.opModifies,  remap)
		opAllocates = remapContextual(self.opAllocates, remap)
		reads       = remapContextual(self.reads,       remap)
		modifies    = remapContextual(self.modifies,    remap)
		allocates   = remapContextual(self.allocates,   remap)
		origin      = self.origin

		return OpAnnotation(invokes, opReads, opModifies, opAllocates, reads, modifies, allocates, origin)

	def compatable(self, codeAnnotation):
		if self.invokes is not None:
			return len(self.invokes[1]) == len(codeAnnotation.contexts)
		return True

class SlotAnnotation(Annotation):
	__slots__ = 'references'

	def __init__(self, references=None):
		#assert references is None or isinstance(references, ContextualAnnotation), type(references)
		self.references = references

	def rewrite(self, references=noMod):
		if references is noMod: references = self.references

		return SlotAnnotation(references)

	def contextSubset(self, remap, invokeMapper=None):
		references = remapContextual(self.references, remap)
		return self.rewrite(references=references)

	def compatable(self, codeAnnotation):
		if self.references is not None:
			return len(self.references[1]) == len(codeAnnotation.contexts)
		return True

emptyCodeAnnotation  = CodeAnnotation(None, False, False, None, None, None, None, None, None, None, None, False, False, False)
emptyOpAnnotation    = OpAnnotation(None, None, None, None, None, None, None, (None,))
emptySlotAnnotation  = SlotAnnotation(None)
