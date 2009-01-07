from __future__ import absolute_import

import util.calling
from . import transferfunctions

class Constraint(object):
	__slots__ = 'parent', 'inputPoint', 'outputPoint',
	
	def __init__(self, sys, inputPoint, outputPoint):
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
		transferfunctions.assignmentConstraint(sys, self.outputPoint, context, self.sourceExpr, self.destinationExpr, configuration, secondary.hits, secondary.misses)


class CopyConstraint(Constraint):
	__slots__ = ()

	def evaluate(self, sys, point, context, configuration, secondary):
		# Simply changes the program point.
		sys.environment.merge(sys, self.outputPoint, context, configuration, secondary)

class SplitMergeInfo(object):
	def __init__(self):
		self.splitLUT = {}
		self.mergeLUT = {}


class SplitConstraint(Constraint):
	__slots__ = 'info'

	def __init__(self, sys, inputPoint, outputPoint, info):
		Constraint.__init__(self, sys, inputPoint, outputPoint)
		self.info = info
		
	def evaluate(self, sys, point, context, configuration, secondary):

		if configuration not in self.info.splitLUT:
			newconfig = sys.canonical.configuration(configuration.object, configuration.region, configuration.currentSet, configuration.currentSet)
			self.info.splitLUT[configuration] = newconfig

			if newconfig.entrySet not in self.info.mergeLUT:
				self.info.mergeLUT[newconfig.entrySet] = set()
			self.info.mergeLUT[newconfig.entrySet].add(configuration)
		else:
			newconfig = self.info.splitLUT[configuration]
	
		sys.environment.merge(sys, self.outputPoint, context, newconfig, secondary)


class MergeConstraint(Constraint):
	__slots__ = 'info'

	def __init__(self, sys, inputPoint, outputPoint, info):
		Constraint.__init__(self, sys, inputPoint, outputPoint)
		self.info = info
	
	def evaluate(self, sys, point, context, configuration, secondary):
		# TODO do we need to reevaluate when the info is updated?

		for oldconfig in self.info.mergeLUT.get(configuration.entrySet, ()):
			newconfig = sys.canonical.configuration(configuration.object, configuration.region, oldconfig.entrySet, configuration.currentSet)
		
			sys.environment.merge(sys, self.outputPoint, context, newconfig, secondary)
