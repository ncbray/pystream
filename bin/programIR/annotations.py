import util.canonical
import collections

noMod = util.canonical.Sentinel('<no mod>')

def ordered(data):
	return tuple(sorted(data))

def remapContextual(cdata, remap, translator=None):
	if cdata is None: return None

	mdata = set()
	cout  = []

	if translator:
		for i in remap:
			if i >= 0:
				data = ordered([translator(item) for item in cdata[1][i]])
				mdata.update(data)
				cout.append(data)
			else:
				cout.append(())

	else:
		for i in remap:
			if i >= 0:
				data = cdata[1][i]
				mdata.update(data)
				cout.append(data)
			else:
				cout.append(())

	return (ordered(mdata), tuple(cout))

Origin = collections.namedtuple('Origin', 'name filename lineno')


class Annotation(object):
	__slots__ = ()


class CodeAnnotation(Annotation):
	__slots__ = 'contexts', 'descriptive', 'staticFold', 'dynamicFold', 'origin'

	def __init__(self, contexts, descriptive, staticFold, dynamicFold, origin):
		self.contexts    = contexts
		self.descriptive = descriptive
		self.staticFold  = staticFold
		self.dynamicFold = dynamicFold
		self.origin      = origin

	def rewrite(self, contexts=noMod, descriptive=noMod,
			staticFold=noMod, dynamicFold=noMod,
			origin=noMod):
		if contexts    is noMod: contexts    = self.contexts
		if descriptive is noMod: descriptive = self.descriptive
		if staticFold  is noMod: staticFold  = self.staticFold
		if dynamicFold is noMod: dynamicFold = self.dynamicFold
		if origin      is noMod: origin      = self.origin

		return CodeAnnotation(contexts, descriptive, staticFold, dynamicFold, origin)

	def contextSubset(self, remap):
		contexts = [self.contexts[i] for i in remap]
		return self.rewrite(contexts=contexts)

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