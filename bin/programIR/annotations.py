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
		if contexts is noMod:    contexts = self.contexts
		if descriptive is noMod: descriptive = self.descriptive
		if fold is noMod:        fold = self.fold
		if original is noMod:    original = self.original

		return CodeAnnotation(contexts, descriptive, fold, original)



class OpAnnotation(Annotation):
	__slots__ = 'invokes', 'reads', 'modifies', 'allocates'

	def __init__(self):
		self.invokes   = None
		self.reads     = None
		self.modifies  = None
		self.allocates = None


class SlotAnnotation(Annotation):
	__slots__ = 'references'

	def __init__(self):
		self.references = None
