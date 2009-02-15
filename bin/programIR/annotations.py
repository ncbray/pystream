import util.canonical

noMod = util.canonical. Sentinel('<no mod>')

class Annotation(object):
	__slots__ = ()


class CodeAnnotation(Annotation):
	__slots__ = 'contexts', 'descriptive', 'fold', 'original'

	def __init__(self, contexts=None, descriptive=False, fold=None, original=None):
		self.contexts    = contexts
		self.descriptive = descriptive
		self.fold        = fold
		self.original    = original

	def rewrite(self, contexts=noMod, descriptive=noMod, fold=noMod, original=noMod):
		if contexts is noMod:    contexts    = self.contexts
		if descriptive is noMod: descriptive = self.descriptive
		if fold is noMod:        fold        = self.fold
		if original is noMod:    original    = self.original

		return CodeAnnotation(contexts, descriptive, fold, original)

	def contextSubset(self, remap):
		contexts = [self.contexts[i] for i in remap]
		return self.rewrite(contexts=contexts)

class OpAnnotation(Annotation):
	__slots__ = 'invokes', 'reads', 'modifies', 'allocates'

	def __init__(self, invokes=None, reads=None, modifies=None, allocates=None):
		self.invokes   = invokes
		self.reads     = reads
		self.modifies  = modifies
		self.allocates = allocates

	def rewrite(self, invokes=noMod, reads=noMod, modifies=noMod, allocates=noMod):
		if invokes is noMod:   invokes   = self.invokes
		if reads is noMod:     reads     = self.reads
		if modifies is noMod:  modifies  = self.modifies
		if allocates is noMod: allocates = self.allocates

		return OpAnnotation(invokes, reads, modifies, allocates)

	def contextSubset(self, remap, invokeMapper):
		if self.invokes is None:
			invokes = None
		else:
			minvokes = set()
			cinvokes = []
			for i in remap:
				inv = self.invokes[1][i]
				inv = tuple(sorted([invokeMapper(dst) for dst in inv]))

				minvokes.update(inv)
				cinvokes.append(inv)
			invokes = (minvokes, tuple(cinvokes))

		return self.rewrite(invokes=invokes)

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