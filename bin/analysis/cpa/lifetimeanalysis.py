import collections

from . import base


from PADS.StrongConnectivity import StronglyConnectedComponents

from analysis.database import structure
from analysis.database import tupleset
from analysis.database import mapping
from analysis.database import lattice

from analysis.astcollector import getOps

import programIR.python.ast as ast


contextSchema   = structure.WildcardSchema()
operationSchema = structure.TypeSchema((ast.Expression, ast.Statement))
functionSchema  = structure.TypeSchema(ast.Function)

def wrapOpContext(schema):
	schema = mapping.MappingSchema(contextSchema, schema)
	schema = mapping.MappingSchema(operationSchema, schema)
	schema = mapping.MappingSchema(functionSchema, schema)
	return schema

def wrapFunctionContext(schema):
	schema = mapping.MappingSchema(contextSchema, schema)
	schema = mapping.MappingSchema(functionSchema, schema)
	return schema


readModifyStruct = structure.StructureSchema(
	('read',   lattice.setUnionSchema),
	('modify', lattice.setUnionSchema)
	)
readModifySchema = wrapOpContext(readModifyStruct)


invokesStruct = structure.StructureSchema(
	('function', functionSchema),
	('context',  contextSchema)
	)
invokesSchema = wrapOpContext(tupleset.TupleSetSchema(invokesStruct))

invokedByStruct = structure.StructureSchema(
	('function',  functionSchema),
	('operation', operationSchema),
	('context',   contextSchema)
	)
invokedBySchema = wrapFunctionContext(tupleset.TupleSetSchema(invokedByStruct))


def invertInvokes(invokes):
	invokedBy = invokedBySchema.instance()

	for func, ops in invokes:
		for op, contexts in ops:
			for context, invs in contexts:
				for dstF, dstC in invs:
					invokedBy[dstF][dstC].add(func, op, context)

	return invokedBy

def filteredSCC(G):
	o = []
	for g in StronglyConnectedComponents(G):
		if len(g) > 1:
			o.append(g)
	return o

# object points to object
# context points to object
# context calls context

# Object may be loop/recursive/stream allocated
# If not, the number of allocations are countable.

#globalHeap = 'global heap'

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
		self.globallyVisible   = obj.context is base.existingObjectContext
		self.externallyVisible = obj.context is base.externalObjectContext


class ReadModifyAnalysis(object):
	def __init__(self, killed, invokedBy):

		# HACK
		self.invokes         = collections.defaultdict(set)
		#self.invokedBy       = collections.defaultdict(set)
		self.invokedBy       = invokedBy
		self.killed          = killed
		
		self.contextReads    = collections.defaultdict(set)
		self.contextModifies = collections.defaultdict(set)

		self.opReads 	     = collections.defaultdict(set)
		self.opModifies      = collections.defaultdict(set)

		self.allReads        = set()
		self.allModifies     = set()

##		self.contextOps      = collections.defaultdict(set)

	
	def process(self, sys):
##		# what contexts are invoked by a given cop
##		for cop, contexts in sys.opInvokes.iteritems():
##			for context in contexts:
##				self.invokedBy[context].add(cop)

		# Copy modifies
		for cop, slots in sys.opModifies.iteritems():
			self.opModifies[(cop.function, cop.op, cop.context)].update(slots)
			self.allModifies.update(slots)

		# Copy Reads
		for cop, slots in sys.opReads.iteritems():
			for slot in slots:
				# Filter static reads.
				if slot in self.allModifies: 
					self.opReads[(cop.function, cop.op, cop.context)].add(slot)
					
			self.allReads.update(slots)


##		# Create context -> cop mapping for all cop
##		for cop in sys.opReads.iterkeys():
##			self.contextOps[cop.context].add(cop)
##		for cop in sys.opModifies.iterkeys():
##			self.contextOps[cop.context].add(cop)
##		for cop in sys.opAllocates.iterkeys():
##			self.contextOps[cop.context].add(cop)
##		for cop in sys.opInvokes.iterkeys():
##			self.contextOps[cop.context].add(cop)


		self.system = sys


		self.processReads()
		self.processModifies()


	def processReads(self):
		self.dirty = set()
		
		for (func, op, context), values in self.opReads.iteritems():
			if values:
				self.contextReads[context].update(values)
				self.dirty.add((func, context))


		while self.dirty:
			current = self.dirty.pop()
			self.processContextReads(current)

	def processContextReads(self, current):
		currentF, currentC = current
		
		for prev in self.invokedBy[currentF][currentC]:
			prevF, prevO, prevC = prev
			
			isDirty = False
			killed = self.killed[(prevC, currentC)]

			# Propigate reads
			for value in self.contextReads[currentC]:
				if value.obj in killed: continue
				
				if value not in self.opReads[prev]:
					self.opReads[prev].add(value)
					self.contextReads[prevC].add(value)
					isDirty = True

			if isDirty: self.dirty.add((prevF, prevC))

	def processModifies(self):
		self.dirty = set()
		
		for (func, op, context), values in self.opModifies.iteritems():
			if values:
				self.contextModifies[context].update(values)
				self.dirty.add((func, context))

		while self.dirty:
			current = self.dirty.pop()
			self.processContextModifies(current)


	def processContextModifies(self, current):
		currentF, currentC = current
		
		for prev in self.invokedBy[currentF][currentC]:
			prevF, prevO, prevC = prev
			
			isDirty = False
			killed = self.killed[(prevC, currentC)]

			# Propigate modifies
			for value in self.contextModifies[currentC]:
				if value.obj in killed: continue
				
				if value not in self.opModifies[prev]:
					self.opModifies[prev].add(value)
					self.contextModifies[prevC].add(value)
					isDirty = True

			if isDirty: self.dirty.add((prevF, prevC))

		
class LifetimeAnalysis(object):
	def __init__(self):
		self.heapReferedToByHeap = collections.defaultdict(set)
		self.heapReferedToByFunc = collections.defaultdict(set)

		self.funcRefersToHeap = collections.defaultdict(set)

		self.allocations = collections.defaultdict(set)


		self.objects = {}

		self.globallyVisible = set()
		self.externallyVisible = set()



	def getObjectInfo(self, obj):
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

		#self.displayHistogram()


	def displayHistogram(self):
		# Display a histogram of the number of live heap objects
		# that may hold (directly or indirectly) a given live heap object.
		hist = collections.defaultdict(lambda:0)
		for obj, info in self.objects.iteritems():
			if not obj in self.escapes:
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
		for context, objs in self.allocations.iteritems():
			func = context.func # HACK
			self.live[(func, context)].update(objs-self.escapes)
			self.dirty.update(self.invokedBy[func][context])

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

		operationSchema.validate(currentO)
		
		newLive = set()

		live = self.live
		
		for dstF, dstC in self.invokes[currentF][currentO][currentC]:
			for dstLive in live[(dstF, dstC)]:
				if dstLive in live[(currentF, currentC)]:
					continue
				if dstLive in newLive:
					continue
				
				refs     = self.funcRefersToHeap[(currentF, currentC)]
				refinfos = [self.getObjectInfo(ref) for ref in refs]

				# Could the object stay live?
				if dstLive in refs:
					# Directly held
					newLive.add(dstLive)
				elif self.objects[dstLive].heldByClosure.intersection(refinfos):
					# Indirectly held
					newLive.add(dstLive)
				else:
					# The object will never propagate along this invocation
					self.killed[(currentC, dstC)].add(dstLive)

		if newLive:
			# Propigate dirty
			live[(currentF, currentC)].update(newLive)
			self.dirty.update(self.invokedBy[currentF][currentC])


	def process(self, sys):
		for slot, values in sys.slots.iteritems():
			if slot.isLocalSlot():
				# HACK search for the "external" function, as it tends to get filted out of the DB.
				context = slot.context
				if context is base.externalFunctionContext:
					for value in values:
						obj = self.getObjectInfo(value)
						obj.localReference.add(context)

						# HACK
						self.funcRefersToHeap[(base.externalFunction, context)].add(value)

						if context is base.externalFunctionContext:
							obj.externallyVisible = True
			else:
				obj = self.getObjectInfo(slot.obj)
				for value in values:
					other = self.getObjectInfo(value)
					obj.refersTo.add(other)
					other.referedFrom.add(obj)

		invokes = invokesSchema.instance()

		for func, funcinfo in sys.db.functionInfos.iteritems():
			ops, lcls = getOps(func)
			for op in ops:
				opinfo = funcinfo.opInfo(op)
				for context, info in opinfo.contexts.iteritems():
					for dstC, dstF in info.invokes:
						invokes[func][op][context].add(dstF, dstC)

			
			for lcl in lcls:
				lclinfo = funcinfo.localInfo(lcl)
				for context, info in lclinfo.contexts.iteritems():
					for ref in info.references:
						obj = self.getObjectInfo(ref)
						obj.localReference.add(func)
						
						self.funcRefersToHeap[(func, context)].add(ref)

						if context is base.externalFunctionContext:
							# Doesn't appear in the database?
							assert False
							obj.externallyVisible = True

		invokedBy = invertInvokes(invokes)


		self.invokes   = invokes
		self.invokedBy = invokedBy
		

		for context, obj in sys.allocations:
			self.allocations[context].add(obj)


		self.propagateVisibility()
		self.propagateHeld()
		self.inferScope()

		self.rm = ReadModifyAnalysis(self.killed, self.invokedBy)
		self.rm.process(sys)
		self.createDB()

	def createDB(self):
		db = readModifySchema.instance()

		# Copy into a database
		for (function, op, context), slots in self.rm.opReads.iteritems():
			db[function][op].merge(context, (slots, None))

		for (function, op, context), slots in self.rm.opModifies.iteritems():
			db[function][op].merge(context, (None, slots))


		self.db = db
