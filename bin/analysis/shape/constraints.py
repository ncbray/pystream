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

class SplitMergeInfo(object):
	def __init__(self, parameters):
		self.parameters = parameters
		self.extendedParameters = set()
		
		self.remoteLUT = {}
		self.localLUT  = {}

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

class SplitConstraint(Constraint):
	__slots__ = 'info'

	def __init__(self, sys, inputPoint, outputPoint, info):
		Constraint.__init__(self, sys, inputPoint, outputPoint)
		self.info = info
		
	def evaluate(self, sys, point, context, configuration, secondary):
		# All the parameters assignments should have been performed.

		localRC, remoteRC = sys.canonical.rcm.split(configuration.currentSet, self.info.srcLocals)

		# TODO filter out bad extended parameters
		epaths = secondary.paths.copy()
		epaths.extendParameters(sys, self.info)

		# Create the local data
		localconfig    = sys.canonical.configuration(configuration.object, configuration.region, configuration.entrySet, localRC)
		localpaths     = sys.canonical.paths(None, None)
		localsecondary = sys.canonical.secondary(localpaths, secondary.externalReferences)

		self.info.registerLocal(sys, remoteRC, localconfig, localsecondary)


		# Create the remote data
		remoteconfig    = sys.canonical.configuration(configuration.object, configuration.region, remoteRC, remoteRC)
		remotesecondary = sys.canonical.secondary(epaths, secondary.externalReferences or bool(localRC))
		
		remotecontext   = context # HACK
		transferfunctions.gcMerge(sys, self.outputPoint, remotecontext, remoteconfig, remotesecondary)

##		print "1"*40
##		print remoteconfig
##		print
##		epaths.dump()



class MergeConstraint(Constraint):
	__slots__ = 'info'

	def __init__(self, sys, inputPoint, outputPoint, info):
		Constraint.__init__(self, sys, inputPoint, outputPoint)
		self.info = info
		info.merge = self # Cirular reference?
	
	def evaluate(self, sys, point, context, configuration, secondary):
		self.info.registerRemote(sys, configuration.entrySet, configuration, secondary)

	def combine(self, sys, context, localIndex, localSecondary, remoteIndex, remoteSecondary):
		mergedRC = sys.canonical.rcm.merge(localIndex.currentSet, remoteIndex.currentSet)
		mergedIndex = sys.canonical.configuration(localIndex.object, localIndex.region, localIndex.entrySet, mergedRC)


		kill = set([p.slot for p in self.info.parameters])
		kill.update([ep.slot for ep in self.info.extendedParameters])
		paths = remoteSecondary.paths.copy(kill)

##		print "2"*40
##		print remoteIndex
##		print
##		paths.dump()


		mergedSecondary = sys.canonical.secondary(paths, localSecondary.externalReferences)

		transferfunctions.gcMerge(sys, self.outputPoint, context, mergedIndex, mergedSecondary)
