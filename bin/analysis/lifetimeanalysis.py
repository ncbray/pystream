import collections
import time

from cpa import base, storegraph
import programIR.python.ast as ast

from PADS.StrongConnectivity import StronglyConnectedComponents

from analysis.database import structure
from analysis.database import tupleset
from analysis.database import mapping
from analysis.database import lattice

from analysis.astcollector import getOps

contextSchema   = structure.WildcardSchema()
operationSchema = structure.TypeSchema((ast.Expression, ast.Statement))
codeSchema  = structure.TypeSchema(ast.Code)

def wrapOpContext(schema):
	schema = mapping.MappingSchema(contextSchema, schema)
	schema = mapping.MappingSchema(operationSchema, schema)
	schema = mapping.MappingSchema(codeSchema, schema)
	return schema

def wrapCodeContext(schema):
	schema = mapping.MappingSchema(contextSchema, schema)
	schema = mapping.MappingSchema(codeSchema, schema)
	return schema



opDataflowSchema = wrapOpContext(lattice.setUnionSchema)

invokesStruct = structure.StructureSchema(
	('code',    codeSchema),
	('context', contextSchema)
	)
invokesSchema = wrapOpContext(tupleset.TupleSetSchema(invokesStruct))

invokedByStruct = structure.StructureSchema(
	('code',      codeSchema),
	('operation', operationSchema),
	('context',   contextSchema)
	)
invokedBySchema = wrapCodeContext(tupleset.TupleSetSchema(invokedByStruct))


def invertInvokes(invokes):
	invokedBy = invokedBySchema.instance()

	for code, ops in invokes:
		assert isinstance(code, ast.Code), type(code)
		for op, contexts in ops:
			for context, invs in contexts:
				for dstCode, dstContext in invs:
					invokedBy[dstCode][dstContext].add(code, op, context)
	return invokedBy

def filteredSCC(G):
	o = []
	for g in StronglyConnectedComponents(G):
		if len(g) > 1:
			o.append(g)
	return o


def objectOfInterest(obj):
	return True
	#return obj.context is not base.external and obj.context is not base.existing

class ObjectInfo(object):
	def __init__(self, obj):
		self.obj            = obj
		self.refersTo       = set()
		self.referedFrom    = set()
		self.localReference = set()
		self.heldByClosure  = set()

		# Reasonable defaults
		self.globallyVisible   = obj.xtype.isExisting()
		self.externallyVisible = obj.xtype.isExternal()

	def isReachableFrom(self, refs):
		return bool(self.heldByClosure.intersection(refs))

class ReadModifyAnalysis(object):
	def __init__(self, sys, invokedBy):
		self.invokedBy       = invokedBy

		self.contextReads    = collections.defaultdict(set)
		self.contextModifies = collections.defaultdict(set)

		self.collectDB(sys)

	def collectDB(self, sys):
		allReads        = set()
		allModifies     = set()

		self.opReadDB   = opDataflowSchema.instance()
		self.opModifyDB = opDataflowSchema.instance()

		self.allocations = collections.defaultdict(set)

		# Copy modifies
		for code in sys.db.liveCode:
			ops, lcls = getOps(code)
			for op in ops:
				for cindex, context in enumerate(code.annotation.contexts):
					if not op.annotation.invokes[0]:
						slots    = op.annotation.modifies[1][cindex]

						self.opModifyDB[code][op].merge(context, slots)
						self.contextModifies[context].update(slots)
						allModifies.update(slots)

		# Copy reads
		for code in sys.db.liveCode:
			# vargs and karg allocations.
			for cindex, context in enumerate(code.annotation.contexts):
				self.allocations[context].update(code.annotation.argobjs[1][cindex])


			ops, lcls = getOps(code)
			for op in ops:
				for cindex, context in enumerate(code.annotation.contexts):
					if not op.annotation.invokes[0]:
						slots    = op.annotation.reads[1][cindex]
						filtered = set([slot for slot in slots if slot in allModifies])

						self.opReadDB[code][op].merge(context, filtered)
						self.contextReads[context].update(filtered)
						allReads.update(slots)

						# Copy allocations.
						if op.annotation.allocates:
							self.allocations[context].update(op.annotation.allocates[1][cindex])


	def process(self, killed):
		self.killed = killed
		self.processReads()
		self.processModifies()


	def processReads(self):
		self.dirty = set()

		for context, values in self.contextReads.iteritems():
			if values: self.dirty.add((context.signature.code, context))


		while self.dirty:
			current = self.dirty.pop()
			self.processContextReads(current)

	def processContextReads(self, current):
		currentF, currentC = current

		for prev in self.invokedBy[currentF][currentC]:
			prevF, prevO, prevC = prev

			prevRead = self.opReadDB[prevF][prevO]

			killed = self.killed[(prevC, currentC)]

			# Propigate reads
			filtered = set([value for value in self.contextReads[currentC] if value.object not in killed])
			current = prevRead[prevC]
			diff = filtered-current if current else filtered

			if diff:
				self.contextReads[prevC].update(diff)
				prevRead.merge(prevC, diff)
				self.dirty.add((prevF, prevC))



	def processModifies(self):
		self.dirty = set()

		for context, values in self.contextModifies.iteritems():
			if values: self.dirty.add((context.signature.code, context))

		while self.dirty:
			current = self.dirty.pop()
			self.processContextModifies(current)

	def processContextModifies(self, current):
		currentF, currentC = current

		for prev in self.invokedBy[currentF][currentC]:
			prevF, prevO, prevC = prev

			prevMod = self.opModifyDB[prevF][prevO]

			killed = self.killed[(prevC, currentC)]

			# Propigate modifies
			filtered = set([value for value in self.contextModifies[currentC] if value.object not in killed])
			#diff = filtered-self.opModifies[prev]
			current = prevMod[prevC]
			diff = filtered-current if current else filtered
			if diff:
				self.contextModifies[prevC].update(diff)
				prevMod.merge(prevC, diff)
				self.dirty.add((prevF, prevC))

class DFSSearcher(object):
	def __init__(self):
		self._stack   = []
		self._touched = set()

	def enqueue(self, *children):
		for child in children:
			if child not in self._touched:
				self._touched.add(child)
				self._stack.append(child)

	def process(self):
		while self._stack:
			current = self._stack.pop()
			self.visit(current)

class ObjectSearcher(DFSSearcher):
	def __init__(self, la):
		DFSSearcher.__init__(self)
		self.la = la

	def visit(self, obj):
		objInfo = self.la.getObjectInfo(obj)
		for slot in obj:
			for next in slot:
				nextInfo = self.la.getObjectInfo(next)
				objInfo.refersTo.add(nextInfo)
				nextInfo.referedFrom.add(objInfo)
				self.enqueue(next)

class LifetimeAnalysis(object):
	def __init__(self):
		self.heapReferedToByHeap = collections.defaultdict(set)
		self.heapReferedToByCode = collections.defaultdict(set)

		self.codeRefersToHeap = collections.defaultdict(set)

		self.objects = {}

		self.globallyVisible = set()
		self.externallyVisible = set()



	def getObjectInfo(self, obj):
		assert isinstance(obj, storegraph.ObjectNode), type(obj)
		if obj not in self.objects:
			info = ObjectInfo(obj)
			self.objects[obj] = info
		else:
			info = self.objects[obj]
		return info


	def findGloballyVisible(self):
		# Globally visible
		active = set()
		for info in self.objects.itervalues():
			if info.globallyVisible:
				active.add(info)
				self.globallyVisible.add(info.obj)

		while active:
			current = active.pop()
			for ref in current.refersTo:
				if not ref.globallyVisible:
					ref.globallyVisible = True
					active.add(ref)
					self.globallyVisible.add(ref.obj)


	def findExternallyVisible(self):
		# Externally visible
		active = set()
		for info in self.objects.itervalues():
			if info.externallyVisible:
				active.add(info)
				self.externallyVisible.add(info.obj)

		while active:
			current = active.pop()
			for ref in current.refersTo:
				if not ref.externallyVisible:
					ref.externallyVisible = True
					active.add(ref)
					self.externallyVisible.add(ref.obj)

	def propagateVisibility(self):
		self.findGloballyVisible()
		self.findExternallyVisible()
		self.escapes = self.globallyVisible.union(self.externallyVisible)


	def propagateHeld(self):
		dirty = set()

		for obj, info in self.objects.iteritems():
			if not obj in self.escapes:
				info.heldByClosure.update(info.referedFrom)
				for dst in info.refersTo:
					if not dst in self.escapes: dirty.add(dst)

		while dirty:
			current = dirty.pop()
			assert current not in self.escapes, current.obj

			# Find the new heldby
			diff = set()
			for prev in current.referedFrom:
				diff.update(prev.heldByClosure-current.heldByClosure)

			if diff:
				# Mark as dirty
				current.heldByClosure.update(diff)
				for dst in current.refersTo:
					if not dst in self.escapes: dirty.add(dst)

		self.displayHistogram()


	def displayHistogram(self):
		# Display a histogram of the number of live heap objects
		# that may hold (directly or indirectly) a given live heap object.
		hist = collections.defaultdict(lambda:0)
		for obj, info in self.objects.iteritems():
			if not obj in self.escapes:
				if len(info.heldByClosure) >= 4:
					print obj
					for other in info.heldByClosure:
						print '\t', other.obj
					print
				hist[len(info.heldByClosure)] += 1
			else:
				hist[-1] += 1

		keys = sorted(hist.iterkeys())
		for key in keys:
			print key, hist[key]

	def inferScope(self):
		# Figure out how far back on the stack the object may propagate
		self.live = collections.defaultdict(set)
		self.killed = collections.defaultdict(set)


		# Seed the inital dirty set
		self.dirty = set()
		for context, objs in self.rm.allocations.iteritems():
			code = context.signature.code # HACK
			self.live[(code, context)].update(objs-self.escapes)
			self.dirty.update(self.invokedBy[code][context])

		while self.dirty:
			current = self.dirty.pop()
			self.processScope(current)

		self.convertKills()


	def convertKills(self):
		# Convert kills on edges to kills on nodes.
		self.contextKilled = collections.defaultdict(set)
		for dstF, contexts in self.invokedBy:
			for dstC, srcs in contexts:

				if srcs:
					killedAll = None
					for srcF, srcO, srcC in srcs:
						newKilled = self.killed[(srcC, dstC)]
						if killedAll is None:
							killedAll = newKilled
						else:
							killedAll = killedAll.intersection(newKilled)
				else:
					killedAll = set()

				if killedAll: self.contextKilled[(dstF, dstC)].update(killedAll)


	def processScope(self, current):
		currentF, currentO, currentC = current
		assert isinstance(currentF, ast.Code), type(currentF)

		operationSchema.validate(currentO)

		newLive = set()

		live = self.live

		for dstF, dstC in self.invokes[currentF][currentO][currentC]:
			for dstLive in live[(dstF, dstC)]:
				if dstLive in live[(currentF, currentC)]:
					continue
				if dstLive in newLive:
					continue

				refs     = self.codeRefersToHeap[(currentF, currentC)]
				refinfos = [self.getObjectInfo(ref) for ref in refs]

				# Could the object stay live?
				if dstLive in refs:
					# Directly held
					newLive.add(dstLive)
				elif self.getObjectInfo(dstLive).isReachableFrom(refinfos):
					# Indirectly held
					newLive.add(dstLive)
				else:
					# The object will never propagate along this invocation
					self.killed[(currentC, dstC)].add(dstLive)

		if newLive:
			# Propigate dirty
			live[(currentF, currentC)].update(newLive)
			self.dirty.update(self.invokedBy[currentF][currentC])


	def gatherInvokes(self, sys):
		invokes = invokesSchema.instance()

		for code in sys.db.liveCode:
			assert isinstance(code, ast.Code), type(code)
			ops, lcls = getOps(code)
			for op in ops:
				if op.annotation.invokes is not None:
					for cindex, context in enumerate(code.annotation.contexts):
						opInvokes = op.annotation.invokes[1][cindex]

						for dstF, dstC in opInvokes:
							assert isinstance(dstF, ast.Code)
							invokes[code][op][context].add(dstF, dstC)


			for lcl in lcls:
				refs = lcl.annotation.references
				if refs is None:
					continue

				for cindex, context in enumerate(code.annotation.contexts):
					for ref in refs[1][cindex]:
						obj = self.getObjectInfo(ref)
						obj.localReference.add(code)

						self.codeRefersToHeap[(code, context)].add(ref)

						if context is base.externalFunctionContext:
							# Doesn't appear in the database?
							assert False
							obj.externallyVisible = True

		invokedBy = invertInvokes(invokes)

		self.invokes   = invokes
		self.invokedBy = invokedBy

	def markVisible(self, lcl, cindex):
		if lcl is not None:
			refs = lcl.annotation.references[1][cindex]
			for ref in refs:
				obj = self.getObjectInfo(ref)
				obj.externallyVisible = True


	def gatherSlots(self, sys):

		searcher = ObjectSearcher(self)

		for code in sys.db.liveCode:
			ops, lcls = getOps(code)
			for lcl in lcls:
				for ref in lcl.annotation.references[0]:
					searcher.enqueue(ref)

			for cindex, context in enumerate(code.annotation.contexts):
				if context.entryPoint:
					self.markVisible(code.selfparam, cindex)
					for param in code.parameters:
						self.markVisible(param, cindex)

					# HACK marks the tuple and the dicitonary visible, which they may not be.
					# NOTE marking the types from the CPA context is insufficient, as there may be
					# "any" slots.
					self.markVisible(code.vparam, cindex)
					self.markVisible(code.kparam, cindex)

					self.markVisible(code.returnparam, cindex)

		searcher.process()


	def process(self, sys):
		self.gatherSlots(sys)
		self.gatherInvokes(sys)
		self.rm = ReadModifyAnalysis(sys, self.invokedBy)


		self.propagateVisibility()
		self.propagateHeld()
		self.inferScope()

		self.rm.process(self.killed)
		self.createDB(sys)

	def createDB(self, sys):
		self.readDB   = self.rm.opReadDB
		self.modifyDB = self.rm.opModifyDB
		self.allocations = self.rm.allocations

		for code in sys.db.liveCode:
			ops, lcls = getOps(code)
			for op in ops:
				if not op.annotation.invokes[0]: continue

				reads    = self.readDB[code][op]
				modifies = self.modifyDB[code][op]

				mr = set()
				rout = []

				mm = set()
				mout = []

				ma = set()
				aout = []

				for cindex, context in enumerate(code.annotation.contexts):
					creads = reads[context]
					if creads:
						mr.update(creads)
						creads = tuple(sorted(creads))
					else:
						creads = ()

					rout.append(creads)

					cmod = modifies[context]
					if cmod:
						mm.update(cmod)
						cmod = tuple(sorted(cmod))
					else:
						cmod = ()
					mout.append(cmod)

				opReads    = (tuple(sorted(mr)), tuple(rout))
				opModifies = (tuple(sorted(mm)), tuple(mout))

				op.rewriteAnnotation(reads=opReads, modifies=opModifies)