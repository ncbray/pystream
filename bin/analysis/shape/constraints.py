from __future__ import absolute_import

import util.calling
from . import transferfunctions


seperateExternal = True

def isPoint(point):
	if isinstance(point, tuple) and len(point) == 2:
		if isinstance(point[1], int):
			return True
	return False

class Constraint(object):
	__slots__ = 'parent', 'inputPoint', 'outputPoint', 'priority'

	def __init__(self, sys, inputPoint, outputPoint):
		assert isPoint(inputPoint),  inputPoint
		assert isPoint(outputPoint), outputPoint
		self.inputPoint = inputPoint
		self.outputPoint = outputPoint
		sys.environment.addObserver(inputPoint, self)

		self.priority = 0

	def update(self, sys, key):
		point, context, index = key

		secondary = sys.environment.secondary(*key)
		self.evaluate(sys, point, context, index, secondary)

	# Intentionally reversed for heapq
	def __lt__(self, other):
		return self.priority > other.priority

	def __gt__(self, other):
		return self.priority < other.priority


class AssignmentConstraint(Constraint):
	__slots__ = 'sourceExpr', 'destinationExpr'

	def __init__(self, sys, inputPoint, outputPoint, sourceExpr, destinationExpr):
		Constraint.__init__(self, sys, inputPoint, outputPoint)

		assert sourceExpr.isExpression(), sourceExpr
		self.sourceExpr      = sourceExpr

		assert destinationExpr.isExpression(), destinationExpr
		self.destinationExpr = destinationExpr


	def evaluate(self, sys, point, context, configuration, secondary):
		transferfunctions.assignmentConstraint(sys, self.outputPoint, context, self.sourceExpr, self.destinationExpr, configuration, secondary.paths, secondary.externalReferences)


	def __repr__(self):
		return "assign(%r -> %r)" % (self.sourceExpr, self.destinationExpr)

class CopyConstraint(Constraint):
	__slots__ = ()

	def evaluate(self, sys, point, context, configuration, secondary):
		# Simply changes the program point.
		transferfunctions.gcMerge(sys, self.outputPoint, context, configuration, secondary)

class ForgetConstraint(Constraint):
	__slots__ = 'forget'

	def __init__(self, sys, inputPoint, outputPoint, forget):
		Constraint.__init__(self, sys, inputPoint, outputPoint)

		for slot in forget:
			assert slot.isSlot(), slot
		self.forget = forget

	def evaluate(self, sys, point, context, configuration, secondary):
		newSecondary = secondary.forget(sys, self.forget)
		newConfig    = configuration.forget(sys, self.forget)
		transferfunctions.gcMerge(sys, self.outputPoint, context, newConfig, newSecondary)


class SplitMergeInfo(object):
	def __init__(self, parameterSlots):
		self.parameterSlots = parameterSlots
		self.extendedParameters = set()

		self.remoteLUT = {}
		self.localLUT  = {}

		# Return value transfer and extended parameter killing
		self.mapping   = {}

	def _mergeLUT(self, splitIndex, index, secondary, lut):
		if splitIndex not in lut:
			lut[splitIndex] = {}

		if not index in lut[splitIndex]:
			lut[splitIndex][index] = secondary.copy()
			changed = True
		else:
			changed = lut[splitIndex][index].merge(secondary)

		return changed


	def makeKey(self, sys, configuration):
		return configuration.rewrite(sys, currentSet=None)

	def registerLocal(self, sys, splitIndex, index, secondary):
		changed = self._mergeLUT(splitIndex, index, secondary, self.localLUT)

		if changed:
			remote = self.remoteLUT.get(splitIndex)
			if remote:
				localIndex = index
				localSecondary = self.localLUT[splitIndex][index]
				context = None # HACK

				for remoteIndex, remoteSecondary in remote.iteritems():
					self.merge.combine(sys, context, localIndex, localSecondary, remoteIndex, remoteSecondary)

	def registerRemote(self, sys, splitIndex, index, secondary):
		changed = self._mergeLUT(splitIndex, index, secondary, self.remoteLUT)

		if changed:
			local = self.localLUT.get(splitIndex)
			if local:
				remoteIndex = index
				remoteSecondary = self.remoteLUT[splitIndex][index]
				context = None # HACK

				for localIndex, localSecondary in local.iteritems():
					self.merge.combine(sys, context, localIndex, localSecondary, remoteIndex, remoteSecondary)

	def addExtendedParameters(self, eparam):
		newParam = eparam-self.extendedParameters
		if newParam:
			for p in newParam:
				assert p and p.isExtendedParameter(), p
				self.mapping[p] = None
			self.extendedParameters.update(newParam)

class SplitConstraint(Constraint):
	__slots__ = 'info'

	def __init__(self, sys, inputPoint, outputPoint, info):
		Constraint.__init__(self, sys, inputPoint, outputPoint)
		self.info = info

	def _accessedCallback(self, slot):
		if slot.isAgedParameter():return False

		# Extended parameter
		if slot.isExpression(): return False

		if slot.isLocal():
			return slot.isParameter()

		if slot.isField() and hasattr(self.info, 'dstLiveFields'):
			return slot.field in self.info.dstLiveFields

		# Unhandled, assumed accessed.
		return True

	def evaluate(self, sys, point, context, configuration, secondary):
		# All the parameters assignments should have been performed.

		# Split the reference count into accessed and non-accessed portions
		localRC, remoteRC = sys.canonical.rcm.split(configuration.currentSet, self._accessedCallback)

		# TODO filter out bad extended parameters (from self-recursive calls?)

		# Add extended parameters to paths
		epaths = secondary.paths.copy()
		epaths.ageExtended(sys.canonical)
		eparams = epaths.extendParameters(sys.canonical, self.info.parameterSlots)
		self.info.addExtendedParameters(eparams)

		# Split the paths into accessed and non-accessed portions
		remotepaths, localpaths = epaths.split(eparams, self._accessedCallback)


		# Create the local data
		localconfig = configuration.rewrite(sys, currentSet=localRC)
		localsecondary = sys.canonical.secondary(localpaths, secondary.externalReferences)

		# Create the remote data

		remoteExternalReferences = configuration.externalReferences or bool(localRC) and seperateExternal

		remoteconfig = configuration.rewrite(sys, entrySet=remoteRC,
				currentSet=remoteRC,
				externalReferences=remoteExternalReferences,
				allocated=False)

		remoteExternalReferences = secondary.externalReferences or bool(localRC)
		remotesecondary = sys.canonical.secondary(remotepaths, remoteExternalReferences)


		# Output the local data
		key = self.info.makeKey(sys, remoteconfig)
		self.info.registerLocal(sys, key, localconfig, localsecondary)


		# Output the remote data
		remotecontext   = context # HACK
		transferfunctions.gcMerge(sys, self.outputPoint, remotecontext, remoteconfig, remotesecondary)

#		print "???", localRC, remoteRC
#		print secondary.externalReferences, remotesecondary.externalReferences



class MergeConstraint(Constraint):
	__slots__ = 'info'

	def __init__(self, sys, inputPoint, outputPoint, info):
		Constraint.__init__(self, sys, inputPoint, outputPoint)
		self.info = info
		info.merge = self # Cirular reference?

	def evaluate(self, sys, point, context, configuration, secondary):
		if configuration.allocated:
			# If it's allocated, there's nothing to merge it with.
			self.remap(sys, context, configuration.currentSet, secondary.paths, configuration, secondary)
		else:
			key = self.info.makeKey(sys, configuration)
			self.info.registerRemote(sys, key, configuration, secondary)

	def combine(self, sys, context, localIndex, localSecondary, remoteIndex, remoteSecondary):
		# Merge the index
		mergedRC = sys.canonical.rcm.merge(localIndex.currentSet, remoteIndex.currentSet)

		# Merge the secondary
		try:
			paths = remoteSecondary.paths.join(localSecondary.paths)
		except:

			return

			print
			print "-"*60
			print 'local'
			print
			print localIndex
			localSecondary.paths.dump()

			print "-"*60
			print 'remote'
			print
			print remoteIndex
			remoteSecondary.paths.dump()

			print "-"*60
			print "Local"
			print
			for k, v in self.info.localLUT.iteritems():
				print k
				for o in v.iterkeys():
					print '\t', o.currentSet
				print
			print "-"*60
			print "Remote"
			print
			for k, v in self.info.remoteLUT.iteritems():
				print k
				for o in v.iterkeys():
					print '\t', o.currentSet
				print
			print

			raise

		self.remap(sys, context, mergedRC, paths, localIndex, localSecondary)

	def remap(self, sys, context, mergedRC, paths, index, secondary):
		# Remap the index
		mergedIndex = index.rewrite(sys, currentSet=mergedRC.remap(sys, self.info.mapping))

		# Remap the secondary
		paths = paths.remap(self.info.mapping)
		paths.unageExtended()
		mergedSecondary = sys.canonical.secondary(paths, secondary.externalReferences)

		if True:
			# Output
			transferfunctions.gcMerge(sys, self.outputPoint, context, mergedIndex, mergedSecondary)
		else:
			print "!"*10
			print mergedRC
			print mergedIndex
			print
