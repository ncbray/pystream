import collections
from language.base.annotation import *

Origin = collections.namedtuple('Origin', 'name filename lineno')

def codeOrigin(code, line=None):
	if line is None: line = code.co_firstlineno
	return Origin(code.co_name, code.co_filename, line)

def functionOrigin(func, line=None):
	return codeOrigin(func.func_code, line)

def originString(origin):
	if origin is not None:
		return "%20s - %s:%d" % origin
	else:
		return "<unknown origin>"

class Annotation(object):
	__slots__ = ()


class CodeAnnotation(Annotation):
	__slots__ = ['contexts', 'descriptive',
		'staticFold', 'dynamicFold',
		'origin',
		'live', 'killed']

	def __init__(self, contexts, descriptive, staticFold, dynamicFold, origin, live, killed):
		self.contexts    = contexts
		self.descriptive = descriptive
		self.staticFold  = staticFold
		self.dynamicFold = dynamicFold
		self.origin      = origin
		self.live        = live
		self.killed      = killed

	def rewrite(self, contexts=noMod, descriptive=noMod,
			staticFold=noMod, dynamicFold=noMod,
			origin=noMod,
			live=noMod, killed=noMod):
		if contexts    is noMod: contexts    = self.contexts
		if descriptive is noMod: descriptive = self.descriptive
		if staticFold  is noMod: staticFold  = self.staticFold
		if dynamicFold is noMod: dynamicFold = self.dynamicFold
		if origin      is noMod: origin      = self.origin
		if live        is noMod: live        = self.live
		if killed      is noMod: killed      = self.killed

		return CodeAnnotation(contexts, descriptive, staticFold, dynamicFold, origin, live, killed)

	def contextSubset(self, remap):
		contexts = [self.contexts[i] for i in remap]
		live     = remapContextual(self.live, remap)
		killed   = remapContextual(self.killed, remap)
		return self.rewrite(contexts=contexts, live=live, killed=killed)

class OpAnnotation(Annotation):
	__slots__ = 'invokes', 'reads', 'modifies', 'allocates', 'origin'

	def __init__(self, invokes, reads, modifies, allocates, origin):
		self.invokes   = invokes
		self.reads     = reads
		self.modifies  = modifies
		self.allocates = allocates
		self.origin    = origin

		assert isinstance(origin, tuple) and not isinstance(origin, Origin)

	def rewrite(self, invokes=noMod, reads=noMod, modifies=noMod, allocates=noMod, origin=noMod):
		if invokes   is noMod: invokes   = self.invokes
		if reads     is noMod: reads     = self.reads
		if modifies  is noMod: modifies  = self.modifies
		if allocates is noMod: allocates = self.allocates
		if origin    is noMod: origin    = self.origin

		return OpAnnotation(invokes, reads, modifies, allocates, origin)

	def contextSubset(self, remap, invokeMapper=None):
		invokes   = remapContextual(self.invokes,   remap, invokeMapper)
		reads     = remapContextual(self.reads,     remap)
		modifies  = remapContextual(self.modifies,  remap)
		allocates = remapContextual(self.allocates, remap)
		origin    = self.origin

		return OpAnnotation(invokes, reads, modifies, allocates, origin)

	def compatable(self, codeAnnotation):
		if self.invokes is not None:
			return len(self.invokes[1]) == len(codeAnnotation.contexts)
		return True

class SlotAnnotation(Annotation):
	__slots__ = 'references'

	def __init__(self, references=None):
		self.references = references

	def rewrite(self, references=noMod):
		if references is noMod: references = self.references

		return SlotAnnotation(references)

	def contextSubset(self, remap):
		references = remapContextual(self.references, remap)
		return self.rewrite(references=references)


emptyCodeAnnotation  = CodeAnnotation(None, False, None, None, None, None, None)
emptyOpAnnotation    = OpAnnotation(None, None, None, None, (None,))
emptySlotAnnotation  = SlotAnnotation(None)
