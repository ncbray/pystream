import util.canonical
import collections

noMod = util.canonical.Sentinel('<no mod>')

ContextualAnnotation = collections.namedtuple('ContextualAnnotation', 'merged context')

def annotationSet(data):
	return tuple(sorted(data))

def makeContextualAnnotation(cdata):
	merged = set()
	for data in cdata: merged.update(data)
	return ContextualAnnotation(annotationSet(merged), tuple(cdata))

def remapContextual(cdata, remap, translator=None):
	if cdata is None: return None

	cout  = []

	for i in remap:
		if i >= 0:
			data = cdata[1][i]
			if translator:
				data = annotationSet([translator(item) for item in data])
		else:
			data = ()
		cout.append(data)

	return makeContextualAnnotation(cout)

Origin = collections.namedtuple('Origin', 'name filename lineno')


class Annotation(object):
	__slots__ = ()


class CodeAnnotation(Annotation):
	__slots__ = 'contexts', 'descriptive', 'staticFold', 'dynamicFold', 'origin', 'argobjs'

	def __init__(self, contexts, descriptive, staticFold, dynamicFold, origin, argobjs):
		self.contexts    = contexts
		self.descriptive = descriptive
		self.staticFold  = staticFold
		self.dynamicFold = dynamicFold
		self.origin      = origin
		self.argobjs     = argobjs

	def rewrite(self, contexts=noMod, descriptive=noMod,
			staticFold=noMod, dynamicFold=noMod,
			origin=noMod, argobjs=noMod):
		if contexts    is noMod: contexts    = self.contexts
		if descriptive is noMod: descriptive = self.descriptive
		if staticFold  is noMod: staticFold  = self.staticFold
		if dynamicFold is noMod: dynamicFold = self.dynamicFold
		if origin      is noMod: origin      = self.origin
		if argobjs     is noMod: argobjs     = self.argobjs

		return CodeAnnotation(contexts, descriptive, staticFold, dynamicFold, origin, argobjs)

	def contextSubset(self, remap):
		contexts = [self.contexts[i] for i in remap]
		argobjs = remapContextual(self.argobjs, remap)
		return self.rewrite(contexts=contexts, argobjs=argobjs)

class OpAnnotation(Annotation):
	__slots__ = 'invokes', 'reads', 'modifies', 'allocates', 'origin'

	def __init__(self, invokes, reads, modifies, allocates, origin):
		self.invokes   = invokes
		self.reads     = reads
		self.modifies  = modifies
		self.allocates = allocates
		self.origin    = origin

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


emptyCodeAnnotation  = CodeAnnotation(None, False, None, None, None, None)
emptyOpAnnotation    = OpAnnotation(None, None, None, None, None)
emptySlotAnnotation  = SlotAnnotation(None)