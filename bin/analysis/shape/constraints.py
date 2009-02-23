from __future__ import absolute_import

import util.calling
from . import transferfunctions

def isPoint(point):
	if isinstance(point, tuple) and len(point) == 2:
		if isinstance(point[1], int):
			return True
	return False

class Constraint(object):
	__slots__ = 'parent', 'inputPoint', 'outputPoint',

	def __init__(self, sys, inputPoint, outputPoint):
		assert isPoint(inputPoint),  inputPoint
		assert isPoint(outputPoint), outputPoint
		self.inputPoint = inputPoint
		self.outputPoint = outputPoint
		sys.environment.addObserver(inputPoint, self)

	def update(self, sys, key):
		point, context, index = key

		secondary = sys.environment.secondary(*key)
		self.evaluate(sys, point, context, index, secondary)


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
				self.mapping[p] = None
			self.extendedParameters.update(newParam)

class SplitConstraint(Constraint):
	__slots__ = 'info'

	def __init__(self, sys, inputPoint, outputPoint, info):
		Constraint.__init__(self, sys, inputPoint, outputPoint)
		self.info = info

	def _accessedCallback(self, slot):
		if slot.isExpression():
			# Extended parameter
			return False
		if slot.isSlot() and slot.isLocal():
			return slot in self.info.parameterSlots
		else:
			return True

	def evaluate(self, sys, point, context, configuration, secondary):
		# All the parameters assignments should have been performed.

		# Split the reference count into accessed and non-accessed portions
		localRC, remoteRC = sys.canonical.rcm.split(configuration.currentSet, self.info.srcLocals)

		# TODO filter out bad extended parameters (from self-recursive calls?)

		# Add extended parameters to paths
		epaths = secondary.paths.copy()
		eparams = epaths.extendParameters(sys.canonical, self.info.parameterSlots)
		self.info.addExtendedParameters(eparams)

		# Split the paths into accessed and non-accessed portions
		remotepaths, localpaths = epaths.split(eparams, self._accessedCallback)


		# Create the local data
		localconfig    = sys.canonical.configuration(configuration.object, configuration.region, configuration.entrySet, localRC)
		localsecondary = sys.canonical.secondary(localpaths, secondary.externalReferences)

		# Output the local data
		self.info.registerLocal(sys, remoteRC, localconfig, localsecondary)


		# Create the remote data
		remoteconfig    = sys.canonical.configuration(configuration.object, configuration.region, remoteRC, remoteRC)
		remotesecondary = sys.canonical.secondary(remotepaths, secondary.externalReferences or bool(localRC))

		# Output the remote data
		remotecontext   = context # HACK
		transferfunctions.gcMerge(sys, self.outputPoint, remotecontext, remoteconfig, remotesecondary)


class MergeConstraint(Constraint):
	__slots__ = 'info'

	def __init__(self, sys, inputPoint, outputPoint, info):
		Constraint.__init__(self, sys, inputPoint, outputPoint)
		self.info = info
		info.merge = self # Cirular reference?

	def evaluate(self, sys, point, context, configuration, secondary):
		self.info.registerRemote(sys, configuration.entrySet, configuration, secondary)

	def combine(self, sys, context, localIndex, localSecondary, remoteIndex, remoteSecondary):
		# Merge the index
		mergedRC = sys.canonical.rcm.merge(localIndex.currentSet, remoteIndex.currentSet)
		mergedRC = mergedRC.remap(sys, self.info.mapping)
		mergedIndex = sys.canonical.configuration(localIndex.object, localIndex.region, localIndex.entrySet, mergedRC)

		# Merge the secondary
		paths = remoteSecondary.paths.join(localSecondary.paths)
		paths = paths.remap(self.info.mapping)
		mergedSecondary = sys.canonical.secondary(paths, localSecondary.externalReferences)

		# Output
		transferfunctions.gcMerge(sys, self.outputPoint, context, mergedIndex, mergedSecondary)
