from __future__ import absolute_import
from programIR.python.ast import Local, Assign

def insertBeforeExit(suite, asgn):
	if suite.blocks and suite.blocks[-1].isControlFlow():
		suite.blocks.insert(-1, asgn) # HACK
	else:
		suite.append(asgn)

def filterPairs(pairs):
	return tuple([(suite, frame) for suite, frame in pairs if frame != None])


class Inserter(object):
	def __init__(self, suite):
		self.suite = suite

	def insert(self, stmt):
		raise NotImplementedError

class HeadInserter(Inserter):
	def insert(self, stmt):
		self.suite.insertHead(stmt)


class TailInserter(Inserter):
	def insert(self, stmt):
		insertBeforeExit(self.suite, stmt)

class Merge(object):
	def __init__(self, pairs):
		self.child 	= None
		self.pairs 	= filterPairs(pairs)

		for suite, frame in self.pairs:
			assert isinstance(suite, Inserter)
			frame.setChild(self)
			
		self.lut 	= {}

	def setChild(self, child):
		assert self.child == None and child != None
		self.child = child


	def propigateMerge(self, oldlcl, newlcl):
		for suite, frame in self.pairs:
			original = frame.readLocal(oldlcl, newlcl)

			if original and newlcl != original:
				asgn = Assign(original, newlcl)
				asgn.markMerge()
				suite.insert(asgn)
				#insertBeforeExit(suite, asgn)

	def doMerge(self, oldlcl, newlcl=None):
		assert isinstance(oldlcl, Local), oldlcl

		
		# Read the original values.
		originals = []

		for suite, frame in self.pairs:
			frame.collectConcrete(oldlcl, originals) 
		
		if not originals: return None

		example = originals[0]
		same = all(map(lambda e: e==example, originals))

		if same:
			return originals[0]
		else:
			if newlcl == None:
				newlcl = Local(oldlcl.name)
##				print "MERGE", newlcl, originals
			self.propigateMerge(oldlcl, newlcl)
			return newlcl

	def readLocal(self, lcl, merge=None):
		assert isinstance(lcl, Local), lcl
		
		if not lcl in self.lut:
			self.lut[lcl] = self.doMerge(lcl, merge)
		return self.lut[lcl]
			

	def collectConcrete(self, lcl, outp):
		if lcl in self.lut:
			outp.append(self.lut[lcl])
		else:
			for suite, frame in self.pairs:
				frame.collectConcrete(lcl, outp)

class LoopMerge(object):
	def __init__(self, suite, parent, read, hot, modify):
		self.child = None
		self.parent = parent
		self.suite = suite

		# Don't set as child, as the merge will later.
		#self.parent.setChild(self)


		self.merged = {}
		self.merge = None

		self.inuse = False

		self.read 	= read
		self.hot 	= hot
		self.modify 	= modify

		self.mask = set()
		self.mask.update(hot)
		#self.mask.update(modify)


		for lcl in self.mask:
			self.merged[lcl] = Local(lcl.name)

	def setChild(self, child):
		assert self.child == None and child != None
		self.child = child
		

	def readLocal(self, lcl, merge=None):
##		print "Loop read local:", lcl, merge, id(self)

		if lcl in self.merged:
			newlcl = self.merged[lcl]
		elif not self.merge:
			newlcl = self.parent.readLocal(lcl, merge)
		else:
			if not self.inuse:
				self.inuse = True
				newlcl = self.merge.readLocal(lcl, merge)
				self.inuse = False
			else:
				newlcl = None

		return newlcl

	def collectConcrete(self, lcl, outp):
##		print "Loop collect:", lcl, outp, id(self)

		if lcl in self.merged:
			outp.append(self.merged[lcl])
		elif not self.merge:
			self.parent.collectConcrete(lcl, outp)
		else:
			if not self.inuse:
				self.inuse = True
				self.merge.collectConcrete(lcl, outp)
				self.inuse = False


	def finalize(self, pairs):
		assert not self.inuse
		assert not self.merge

		pairs.append((self.suite, self.parent))
		pairs = filterPairs(pairs)

		self.merge = Merge(pairs)

		self.inuse = True
		for oldlcl, newlcl in self.merged.iteritems():
			merged = self.merge.readLocal(oldlcl, newlcl)
			assert merged == newlcl, (newlcl, merged)

		self.inuse = False

class Split(object):
	def __init__(self, parent):
		assert parent
		self.children = set()
		self.parent = parent
		self.parent.setChild(self)

		self.inuse = False

	def setChild(self, child):
		assert child
		assert not child in self.children
		self.children.add(child)

	def readLocal(self, lcl, merge=None):
		# Deliberately filters out merge fuzing.
		return self.parent.readLocal(lcl)

	def collectConcrete(self, lcl, outp):
		if not self.inuse:
			self.inuse = True
			self.parent.collectConcrete(lcl, outp)
			self.inuse = False

def mergeFrames(pairs):
	return LocalFrame(Merge(pairs))

class ExceptionMerge(object):
	def __init__(self, exceptLocals):
		self.exceptLocals = exceptLocals

	def __get(self, lcl):
		if not lcl in self.exceptLocals:
			self.exceptLocals[lcl] = Local(lcl.name)
		return self.exceptLocals[lcl]

	def setChild(self, child):
		pass
		
	def collectConcrete(self, lcl, outp):
		outp.append(self.__get(lcl))


	def readLocal(self, lcl, merge=None):
		return self.__get(lcl)


class LocalFrame(object):
	def __init__(self, parent=None):
		self.child 	= None
		self.parent 	= parent
		
		if parent: parent.setChild(self)
		
		self.lut = {}

	def setChild(self, child):
		assert self.child == None and child != None
		self.child = child

	def readLocal(self, lcl, merge=None):
		assert isinstance(lcl, Local)
		
		if not lcl in self.lut:
			outp = self.parent.readLocal(lcl, merge) if self.parent else None
			self.lut[lcl] = outp
		else:
			outp = self.lut[lcl]

		assert outp == None or isinstance(outp, Local), outp
		return outp

	def writeLocal(self, lcl):
		assert isinstance(lcl, Local)

		# Rename the local.
		newlcl = Local(lcl.name)
		self.lut[lcl] = newlcl
		
		return newlcl

	def redefineLocal(self, oldlcl, newlcl):
		assert isinstance(oldlcl, Local), oldlcl
		assert isinstance(newlcl, Local), newlcl

		self.lut[oldlcl] = newlcl

	def deleteLocal(self, lcl):
		assert isinstance(lcl, Local), lcl
		assert lcl in self.lut and self.lut[lcl] != None
		self.lut[lcl] = None


	def collectConcrete(self, lcl, outp):
		if lcl in self.lut:
			outp.append(self.lut[lcl])
		elif self.parent:
			self.parent.collectConcrete(lcl, outp)

	def split(self):
		split = Split(self)
		return LocalFrame(split), LocalFrame(split)

