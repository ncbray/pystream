from util.typedispatch import *

from language.python.ast import Local

from . numbering import contains

class ReadModify(object):
	def __init__(self):
		self._read = set()
		self._modify = set()

	def read(self, lcl):
		if not lcl in self._modify:
			self._read.add(lcl)

	def modify(self, lcl):
		self._modify.add(lcl)

	def absorbChild(self, child):
		self._read.update(child._read.difference(self._modify))
		self._modify.update(child._modify)


class PlaceFrame(object):
	def __init__(self):
		self.normal 	= ReadModify()
		self.breaks 	= []
		self.continues 	= []
		self.raises 	= []
		self.returns	= []

	def doBreak(self):
		self.breaks.append(self.normal._modify)
		self.normal._modify = set()

	def doContinue(self):
		self.continues.append(self.normal._modify)
		self.normal._modify = set()

	def doRaise(self):
		self.raises.append(self.normal._modify)
		self.normal._modify = set()

	def doReturn(self):
		self.returns.append(self.normal._modify)
		self.normal._modify = set()


	def absorbExceptional(self, other):
		self.breaks.extend(other.breaks)
		self.continues.extend(other.continues)
		self.raises.extend(other.raises)
		self.returns.extend(other.returns)

	def mergeChild(self, child):
		self.normal.absorbChild(child.normal)
		self.absorbExceptional(child)

def mergeReadModifyParallel(rms):
	outp = ReadModify()
	for rm in rms:
		if rm:
			outp._read.update(rm._read)
			outp._modify.update(rm._modify)
	return outp


def mergeFramesParallel(frames):
	outp = PlaceFrame()

	normals = [frame.normal for frame in frames]
	outp.normal = mergeReadModifyParallel(normals)

	for frame in frames:
		outp.absorbExceptional(frame)

	return outp

class PlaceFlowFunctions(TypeDispatcher):
	__namedispatch__ = True # HACK emulates old visitor	
	
	def __init__(self, numbering):
		super(PlaceFlowFunctions, self).__init__()
		self.frame = PlaceFrame()

		self.annotate = {}
		self.numbering = numbering

		self.exceptRead = set()
		self.hasExceptionHandling = False

	@dispatch(str, int, float, type(None))
	def visitLeaf(self, node):
		pass

	@defaultdispatch
	def default(self, node):
		node.visitChildren(self)

	def visitLocal(self, node):
		self.frame.normal.read(node)

	def visitAssign(self, node):
		self(node.expr)

		for lcl in node.lcls:
			self.frame.normal.modify(lcl)

	def visitUnpackSequence(self, node):
		self(node.expr)
		for target in node.targets:
			self.frame.normal.modify(target)

	def visitReturn(self, node):
		node.visitChildren(self)
		self.frame.doReturn()

	def visitContinue(self, node):
		self.frame.doContinue()

	def visitBreak(self, node):
		self.frame.doBreak()

	def visitRaise(self, node):
		node.visitChildren(self)
		self.frame.doRaise()

	def filterMerges(self, node, merges):
		return tuple([m for m in merges if not contains(self.numbering[node], self.numbering[m])])


	def visitExceptionHandler(self, node):
		self(node.preamble)
		self(node.type)

		if isinstance(node.value, Local):
			self.frame.normal.modify(node.value)
		else:
			self(node.value)

		self(node.body)


	def visitTryExceptFinally(self, node):
		# HACK
		self.hasExceptionHandling = True

		self(node.body)

		old = self.frame


		exceptional = []
		for handler in node.handlers:
			self.hasExceptionHandling = True
			self.frame = f = PlaceFrame()
			self(handler)
			exceptional.append(f)

		if node.defaultHandler:
			self.hasExceptionHandling = True
			self.frame = f = PlaceFrame()
			self(node.defaultHandler)
			exceptional.append(f)

		merged = mergeFramesParallel(exceptional)


		reads = tuple(merged.normal._read)
		modifies = self.filterMerges(node, merged.normal._modify)


		self.exceptRead.update(reads)

		self.frame = els = PlaceFrame()
		self(node.else_)


		self.frame = fin = PlaceFrame()
		self(node.finally_)

		freads = tuple(fin.normal._read)
		fmodifies = self.filterMerges(node, fin.normal._modify)


		self.annotate[node] = (reads, modifies, freads, fmodifies)

		merged = mergeFramesParallel((merged, els, fin))
		old.mergeChild(merged)
		self.frame = old

	def visitSwitch(self, node):
		self(node.condition)

		assert self.frame.normal

		old = self.frame


		t = PlaceFrame()
		self.frame = t
		self(node.t)


		f = PlaceFrame()
		self.frame = f
		self(node.f)


		merged = mergeFramesParallel((t, f))

		tosplit = tuple(merged.normal._read)
		tomerge = tuple(merged.normal._modify)

		tomerge = self.filterMerges(node, tomerge)

		self.annotate[node] = (tosplit, tomerge)


		old.mergeChild(merged)


		self.frame = old

	def visitWhile(self, node):
		old = self.frame

		body = PlaceFrame()
		self.frame = body



		self(node.condition)
		self(node.body)


		# Merge in the continues.
		merge = set()
		merge.update(body.normal._modify)
		for c in self.frame.continues:
			merge.update(c)
		self.frame.continues = []
		body.normal._modify.update(merge)

		timewarp 	= tuple(body.normal._read.intersection(merge))
		loopread 	= tuple(body.normal._read.difference(timewarp))
		loopmodify	= tuple(merge.difference(timewarp))


		breaks = self.frame.breaks
		self.frame.breaks = []

		# Evaluate the else block
		self(node.else_)



		if breaks:
			merge = set()
			merge.update(body.normal._modify)
			for b in breaks:
				merge.update(b)
			body.normal._modify.update(merge)

			breakmerge = tuple(body.normal._modify)

			breakmerge = self.filterMerges(node, breakmerge)
		else:
			breakmerge = ()


		self.annotate[node] = (loopread, timewarp, loopmodify, breakmerge)

		old.mergeChild(self.frame)

		self.frame = old


	def visitFor(self, node):
		self(node.iterator)

		old = self.frame

		body = PlaceFrame()
		self.frame = body

		if isinstance(node.index, Local):
			self.frame.normal.modify(node.index)
		else:
			self(node.index)

		self(node.body)


		# Merge in the continues.
		merge = set()
		merge.update(body.normal._modify)
		for c in self.frame.continues:
			merge.update(c)
		self.frame.continues = []
		body.normal._modify.update(merge)

		timewarp 	= tuple(body.normal._read.intersection(merge))
		loopread 	= tuple(body.normal._read.difference(timewarp))
		loopmodify	= tuple(merge.difference(timewarp))


		breaks = self.frame.breaks
		self.frame.breaks = []


		# Evaluate the else block
		self(node.else_)



		if breaks:
			merge = set()
			merge.update(body.normal._modify)
			for b in breaks:
				merge.update(b)
			body.normal._modify.update(merge)

			breakmerge = tuple(body.normal._modify)

			breakmerge = self.filterMerges(node, breakmerge)
		else:
			breakmerge = ()


		self.annotate[node] = (loopread, timewarp, loopmodify, breakmerge)

		old.mergeChild(self.frame)

		self.frame = old


	def process(self, node):
		old = self.frame

		self.frame = PlaceFrame()

		self(node.ast)

		result = self.frame
		assert not result.breaks, result.breaks
		assert not result.continues, result.continues

		self.frame = old
