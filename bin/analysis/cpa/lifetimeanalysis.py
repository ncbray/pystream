import collections

from . import base

from PADS.StrongConnectivity import StronglyConnectedComponents

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

globalHeap = 'global heap'

def objectOfInterest(obj):
	return True
	#return obj.context is not base.external and obj.context is not base.existing

class ObjectInfo(object):
	def __init__(self, obj):
		self.obj = obj
		self.refersTo = set()
		self.referedFrom = set()
		self.localReference = set()

		self.heldByClosure = set()

		# Reasonable defaults
		self.globallyVisible   = obj.context is base.existingObjectContext
		self.externallyVisible = obj.context is base.externalObjectContext


	def process(self, sys):
		for srcop, dstfunc in sys.invocations:
			self.invokes[srcop.context].add(dstfunc.context)
			self.invokedBy[dstfunc.context].add(srcop.context)

		for context, slot in sys.contextModifies:
			self.contextModifies[context].add(slot)
			self.allModifies.add(slot)

		for context, slot in sys.contextReads:
			# Eliminates static reads.
			if slot in self.allModifies:
				self.contextReads[context].add(slot)

			self.allReads.add(slot)
			
		self.inferReadModify()

class ReadModifyAnalysis(object):
	def __init__(self, killed):

		# HACK
		self.invokes         = collections.defaultdict(set)
		self.invokedBy       = collections.defaultdict(set)
		self.killed          = killed
		
		self.contextReads    = collections.defaultdict(set)
		self.contextModifies = collections.defaultdict(set)

		self.opReads 	     = collections.defaultdict(set)
		self.opModifies      = collections.defaultdict(set)

		self.allReads        = set()
		self.allModifies     = set()

		self.contextOps      = collections.defaultdict(set)

	
	def process(self, sys):
		# what contexts are invoked by a given cop
		for cop, contexts in sys.opInvokes.iteritems():
			for context in contexts:
				self.invokedBy[context].add(cop)

		# Copy modifies
		for cop, slots in sys.opModifies.iteritems():
			self.opModifies[cop].update(slots)
			self.allModifies.update(slots)

		# Copy Reads
		for cop, slots in sys.opReads.iteritems():
			for slot in slots:
				# Filter static reads.
				if slot in self.allModifies: 
					self.opReads[cop].add(slot)
					
			self.allReads.update(slots)


		# Create context -> cop mapping for all cop
		for cop in sys.opReads.iterkeys():
			self.contextOps[cop.context].add(cop)
		for cop in sys.opModifies.iterkeys():
			self.contextOps[cop.context].add(cop)
		for cop in sys.opAllocates.iterkeys():
			self.contextOps[cop.context].add(cop)
		for cop in sys.opInvokes.iterkeys():
			self.contextOps[cop.context].add(cop)


		self.system = sys


		# Initalize the dirty set		
		dirty = set()
		
		for cop, values in self.opReads.iteritems():
			self.contextReads[cop.context].update(values)
			if values: dirty.add(cop)

		for cop, values in self.opModifies.iteritems():
			self.contextModifies[cop.context].update(values)
			if values: dirty.add(cop)

		while dirty:
			self.processContext(dirty)


	def processContext(self, dirty):
		current = dirty.pop()

		# Copy the op read/modifies into the context
		self.contextReads[current.context].update(self.opReads[current])
		self.contextModifies[current.context].update(self.opModifies[current])
		
		for prev in self.invokedBy[current.context]:
			killed = self.killed[(prev.context, current.context)]
			isDirty = False

			for value in self.contextReads[current.context]:
				if value.obj in killed:
					continue
				
				if value not in self.opReads[prev]:
					self.opReads[prev].add(value)
					self.contextReads[prev.context].add(value)
					isDirty = True

			for value in self.contextModifies[current.context]:
				if value.obj in killed:
					continue
				
				if value not in self.opModifies[prev]:
					self.opModifies[prev].add(value)
					self.contextModifies[prev.context].add(value)
					isDirty = True

			if isDirty: dirty.add(prev)

		
class LifetimeAnalysis(object):
	def __init__(self):
		self.heapReferedToByHeap = collections.defaultdict(set)
		self.heapReferedToByFunc = collections.defaultdict(set)

		self.funcRefersToHeap = collections.defaultdict(set)

		self.allocations = collections.defaultdict(set)


		self.invokes   = collections.defaultdict(set)
		self.invokedBy = collections.defaultdict(set)


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


	def propagateVisibility(self):
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
			
			diff = set()
			for prev in current.referedFrom:
				diff.update(prev.heldByClosure-current.heldByClosure)

			if diff:
				current.heldByClosure.update(diff)
				for dst in current.refersTo:
					if not dst in self.escapes: dirty.add(dst)	


		# Display a histogram of the number of live heap objects
		# that may hold (directly or indirectly) a given live heap object.
		hist = collections.defaultdict(lambda:0)
		for obj, info in self.objects.iteritems():
			if not obj in self.escapes:
				hist[len(info.heldByClosure)] += 1
			else:
				hist[-1] += 1

##		keys = sorted(hist.iterkeys())
##		for key in keys:
##			print key, hist[key]

	def inferScope(self):
		# Figure out how far back on the stack the object may propagate


		live = collections.defaultdict(set)
		killed = collections.defaultdict(set)


		dirty = set()
		for context, objs in self.allocations.iteritems():
			live[context].update(objs-self.escapes)
			dirty.update(self.invokedBy[context])


		while dirty:
			current = dirty.pop()
			currentLive = set()
			currentKilled = set()
			for dst in self.invokes[current]:
				for dstLive in live[dst]:
					if dstLive not in live[current] and dstLive not in currentLive:
						refs = self.funcRefersToHeap[current]

						refinfos = [self.getObjectInfo(ref) for ref in refs]
						# Could the object stay live?
						if dstLive in refs:
							currentLive.add(dstLive)
						elif self.objects[dstLive].heldByClosure.intersection(refinfos):
							currentLive.add(dstLive)
						else:
							# The object will never propagate along this invocation
							killed[(current, dst)].add(dstLive)

			if currentLive:
				live[current].update(currentLive)
				dirty.update(self.invokedBy[current])

		self.contextLive = live
		self.killed = killed

		self.contextKilled = collections.defaultdict(set)
		
		for dst, srcs in self.invokedBy.iteritems():
			if srcs:
				killedAll = None
				for src in srcs:
					newKilled = killed[(src, dst)]
					if killedAll is None:
						killedAll = newKilled
					else:
						killedAll = killedAll.intersection(newKilled)
			else:
				killedAll = set()

			self.contextKilled[dst].update(killedAll)


	def process(self, sys):
		for slot, values in sys.slots.iteritems():
			if slot.isLocalSlot():
				func = slot.context
				for value in values:
					obj = self.getObjectInfo(value)
					obj.localReference.add(func)
					
					self.funcRefersToHeap[func].add(value)

					if slot.context is base.externalFunctionContext:
						obj.externallyVisible = True
			else:
				obj = self.getObjectInfo(slot.obj)
				for value in values:
					other = self.getObjectInfo(value)
					obj.refersTo.add(other)
					other.referedFrom.add(obj)

		for srcop, dstfunc in sys.invocations:
			self.invokes[srcop.context].add(dstfunc.context)
			self.invokedBy[dstfunc.context].add(srcop.context)

		for context, obj in sys.allocations:
			self.allocations[context].add(obj)


			


		self.propagateVisibility()
		self.propagateHeld()
		self.inferScope()

		self.rm = ReadModifyAnalysis(self.killed)
		self.rm.process(sys)
		
##		groups = filteredSCC(dict(self.heapReferedToByHeap))
