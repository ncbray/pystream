from __future__ import absolute_import

# Points of variation
# 	Store Arangement
#		Single
#		Per function
#		Per program point
#	Observers
#		Per store
#		Per index

# Shape analysis
# Full index:
#	('shape', function, fsid, context, configuration) -> secondary
# Observer index:
#	('shape', function, fsid, context) -> observer set

class DataflowEnvironment(object):
	__slots__ = '_secondary', 'observers'

	def __init__(self):
		self._secondary   = {}
		self.observers = {}

	def addObserver(self, index, constraint):
		if not index in self.observers:
			self.observers[index] = set((constraint,))
		else:
			self.observers[index].add(constraint)

	def merge(self, sys, point, context, index, secondary):
		assert not secondary.paths.containsAged()

		# Do the merge
		key = (point, context, index)
		if not key in self._secondary:
			self._secondary[key] = secondary.copy()
			changed = True
		else:
			changed = self._secondary[key].merge(secondary)

		# Did we discover any new information?
		if changed and point in self.observers:
			# Make sure the consumers will be re-evaluated.
			for observer in self.observers[point]:
				sys.worklist.addDirty(observer, key)

	def secondary(self, point, context, index):
		key = (point, context, index)
		return self._secondary.get(key)


# Processes the queue depth first.
class Worklist(object):
	def __init__(self):
		self.worklist = []
		self.dirty = set()
		self.maxLength = 0
		self.steps = 0
		self.usefulSteps = 0

	def addDirty(self, constraint, index):
		self.useful = True
		key = (constraint, index)
		if key not in self.dirty:
			self.dirty.add(key)
			self.worklist.append(key)

	def step(self, sys, trace=False):
		# Track statistics
		self.maxLength = max(len(self.worklist), self.maxLength)

		if trace:
			if self.steps%100==0: print ".",
			if self.steps%10000==0:
				print
				sys.dumpStatistics()
		self.steps += 1

		# Process a constraint/index pair
		key = self.worklist.pop()
		self.dirty.remove(key)

		constraint, index = key

		self.useful = False

		try:
			constraint.update(sys, index)
		except:
			print "ERROR processing:", constraint, constraint.inputPoint, constraint.outputPoint
			raise

		if self.useful: self.usefulSteps += 1

	def process(self, sys, trace=False, limit=0):
		stop = self.steps+limit
		while self.worklist:
			self.step(sys, trace)

			if limit and self.steps >= stop:
				return False

		return True
